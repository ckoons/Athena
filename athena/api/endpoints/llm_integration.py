"""
Athena API Endpoints for LLM Integration

Provides REST API endpoints for LLM-powered knowledge graph operations.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from fastapi.responses import StreamingResponse

from tekton.core.llm_client import TektonLLMClient

from athena.api.models.llm import (
    KnowledgeContextRequest,
    KnowledgeContextResponse,
    KnowledgeChatRequest,
    KnowledgeChatResponse,
    EntityExtractionRequest,
    EntityExtractionResponse,
    RelationshipInferenceRequest,
    RelationshipInferenceResponse
)
from athena.core.engine import get_knowledge_engine
from athena.core.entity import Entity
from athena.core.relationship import Relationship

logger = logging.getLogger("athena.api.llm_integration")

router = APIRouter(prefix="/llm", tags=["llm"])
llm_client = TektonLLMClient(component_id="athena.knowledge")

@router.post("/knowledge/context", response_model=KnowledgeContextResponse)
async def get_knowledge_context(request: KnowledgeContextRequest):
    """
    Get relevant knowledge context for a query from the knowledge graph.
    
    This endpoint retrieves entities, relationships, and structured context
    that are relevant to the given query, to be used for enhancing LLM responses.
    """
    engine = await get_knowledge_engine()
    
    try:
        # Search for relevant entities based on query
        entities = await engine.search_entities(
            query=request.query,
            limit=request.max_entities or 5
        )
        
        # Get relationships between these entities
        relationships = []
        entity_ids = [e.entity_id for e in entities]
        
        # For each entity, get its relationships
        for entity_id in entity_ids:
            entity_relationships = await engine.get_entity_relationships(
                entity_id=entity_id,
                direction="both"
            )
            
            # Only include relationships between our relevant entities
            for rel, connected_entity in entity_relationships:
                if connected_entity.entity_id in entity_ids:
                    relationships.append(rel)
        
        # Construct knowledge context
        context = {
            "entities": [e.to_dict() for e in entities],
            "relationships": [r.to_dict() for r in relationships]
        }
        
        return KnowledgeContextResponse(
            query=request.query,
            entities=entities,
            relationships=relationships,
            context=context
        )
    
    except Exception as e:
        logger.error(f"Error getting knowledge context: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving knowledge context: {str(e)}")

@router.post("/chat", response_model=KnowledgeChatResponse)
async def knowledge_chat(request: KnowledgeChatRequest):
    """
    Generate a knowledge-enhanced chat response using the LLM.
    
    This endpoint enhances the LLM response with information from the knowledge graph.
    """
    engine = await get_knowledge_engine()
    
    try:
        # First, get relevant knowledge context
        knowledge_context = await get_knowledge_context(
            KnowledgeContextRequest(
                query=request.query,
                max_entities=request.max_entities
            )
        )
        
        # Construct system prompt with knowledge context
        system_prompt = f"""
        You are a knowledge-enhanced assistant with access to a knowledge graph.
        Use the provided knowledge context to inform your responses.
        
        The knowledge context contains:
        1. Entities related to the conversation
        2. Relationships between entities
        3. Properties and attributes of entities
        
        When referring to entities in the knowledge graph, use the format [[Entity Name:entity_id:entity_type]].
        Reference specific entities and relationships when appropriate.
        If you don't know something based on the provided knowledge, say so rather than making up information.
        
        Knowledge Context:
        {json.dumps(knowledge_context.context, indent=2)}
        """
        
        # Generate LLM response
        llm_response = await llm_client.generate_text(
            prompt=request.query,
            system_prompt=system_prompt,
            model=request.model,
            provider=request.provider
        )
        
        # Extract entities mentioned in the response
        entity_ids = set()
        for entity in knowledge_context.entities:
            if entity.name.lower() in llm_response.content.lower():
                entity_ids.add(entity.entity_id)
        
        mentioned_entities = [
            entity for entity in knowledge_context.entities
            if entity.entity_id in entity_ids
        ]
        
        return KnowledgeChatResponse(
            query=request.query,
            answer=llm_response.content,
            entities=mentioned_entities,
            context_entities=knowledge_context.entities
        )
    
    except Exception as e:
        logger.error(f"Error in knowledge chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating chat response: {str(e)}")

@router.post("/chat/stream")
async def stream_knowledge_chat(request: KnowledgeChatRequest, background_tasks: BackgroundTasks):
    """
    Stream a knowledge-enhanced chat response using the LLM.
    
    This endpoint enhances the LLM response with information from the knowledge graph
    and streams the response as it's generated.
    """
    engine = await get_knowledge_engine()
    
    async def generate_stream():
        try:
            # First, get relevant knowledge context
            knowledge_context = await get_knowledge_context(
                KnowledgeContextRequest(
                    query=request.query,
                    max_entities=request.max_entities
                )
            )
            
            # Construct system prompt with knowledge context
            system_prompt = f"""
            You are a knowledge-enhanced assistant with access to a knowledge graph.
            Use the provided knowledge context to inform your responses.
            
            The knowledge context contains:
            1. Entities related to the conversation
            2. Relationships between entities
            3. Properties and attributes of entities
            
            When referring to entities in the knowledge graph, use the format [[Entity Name:entity_id:entity_type]].
            Reference specific entities and relationships when appropriate.
            If you don't know something based on the provided knowledge, say so rather than making up information.
            
            Knowledge Context:
            {json.dumps(knowledge_context.context, indent=2)}
            """
            
            # Track which entities are mentioned
            mentioned_entities = set()
            
            # Stream the response
            async for chunk in llm_client.stream_text(
                prompt=request.query,
                system_prompt=system_prompt,
                model=request.model,
                provider=request.provider
            ):
                # Check for entity mentions in this chunk
                for entity in knowledge_context.entities:
                    if entity.name.lower() in chunk.content.lower():
                        mentioned_entities.add(entity.entity_id)
                
                # Yield the chunk
                yield json.dumps({
                    "content": chunk.content,
                    "done": False
                }) + "\n"
            
            # Final message with entity information
            entities_data = [
                entity.to_dict() for entity in knowledge_context.entities
                if entity.entity_id in mentioned_entities
            ]
            
            yield json.dumps({
                "content": "",
                "done": True,
                "entities": entities_data
            }) + "\n"
            
        except Exception as e:
            logger.error(f"Error in streaming knowledge chat: {e}")
            yield json.dumps({
                "error": f"Error generating chat response: {str(e)}",
                "done": True
            }) + "\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="application/json"
    )

@router.post("/entities/extract", response_model=EntityExtractionResponse)
async def extract_entities(request: EntityExtractionRequest):
    """
    Extract entities from text using the LLM.
    
    This endpoint uses the LLM to identify and extract entities from the provided text.
    """
    engine = await get_knowledge_engine()
    
    try:
        # Construct system prompt for entity extraction
        system_prompt = """
        You are an entity extraction assistant specialized in named entity recognition.
        Extract entities from the provided text and categorize them by type.
        
        For each entity, include:
        1. Entity name (canonical form)
        2. Entity type (person, organization, location, concept, event, product, technology, or other)
        3. Any aliases mentioned in the text
        4. Any attributes or properties mentioned
        5. Confidence level (high, medium, low)
        
        Format your response as JSON with an "entities" array containing each entity.
        Each entity should have the following structure:
        {
            "name": "Entity Name",
            "type": "entity_type",
            "aliases": ["Alias 1", "Alias 2"],
            "properties": {"property1": "value1", "property2": "value2"},
            "confidence": 0.9
        }
        
        Only extract entity types specified in the entity_types list, if provided.
        Otherwise, extract all entities you can identify.
        """
        
        prompt = request.text
        if request.entity_types:
            entity_types_str = ", ".join(request.entity_types)
            prompt = f"Entity types to extract: {entity_types_str}\n\nText: {request.text}"
        
        # Call LLM
        llm_response = await llm_client.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=request.model,
            provider=request.provider,
            response_format="json"
        )
        
        # Parse LLM response
        try:
            # Extract JSON from response
            json_content = llm_response.content
            if isinstance(json_content, str):
                # Find JSON in the string if needed
                if "{" in json_content and "}" in json_content:
                    start = json_content.find("{")
                    end = json_content.rfind("}") + 1
                    json_content = json_content[start:end]
                
                response_data = json.loads(json_content)
            else:
                response_data = json_content
            
            # Create Entity objects from extracted data
            entities = []
            for entity_data in response_data.get("entities", []):
                entity = Entity(
                    entity_type=entity_data.get("type", "unknown"),
                    name=entity_data.get("name", ""),
                    properties=entity_data.get("properties", {}),
                    confidence=entity_data.get("confidence", 0.5),
                    source="llm_extraction"
                )
                
                # Add aliases
                for alias in entity_data.get("aliases", []):
                    entity.add_alias(alias)
                
                entities.append(entity)
            
            return EntityExtractionResponse(
                text=request.text,
                entities=entities,
                raw_extraction=response_data
            )
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response as JSON: {e}")
            logger.debug(f"Raw response: {llm_response.content}")
            raise HTTPException(status_code=500, detail="Failed to parse entity extraction response")
    
    except Exception as e:
        logger.error(f"Error extracting entities: {e}")
        raise HTTPException(status_code=500, detail=f"Error extracting entities: {str(e)}")

@router.post("/relationships/infer", response_model=RelationshipInferenceResponse)
async def infer_relationships(request: RelationshipInferenceRequest):
    """
    Infer relationships between entities using the LLM.
    
    This endpoint uses the LLM to identify and infer relationships between the provided entities.
    """
    engine = await get_knowledge_engine()
    
    try:
        # Get entities if only IDs are provided
        entities = []
        for entity_id in request.entity_ids:
            entity = await engine.get_entity(entity_id)
            if entity:
                entities.append(entity.to_dict())
        
        if not entities:
            raise HTTPException(status_code=400, detail="No valid entities found")
        
        # Construct system prompt for relationship inference
        system_prompt = """
        You are a knowledge relationship inference assistant.
        Analyze the provided entities and identify potential relationships between them.
        
        For each relationship, include:
        1. Source entity ID
        2. Target entity ID
        3. Relationship type (e.g., works_for, knows, located_in, created, part_of, uses)
        4. Direction (outgoing, incoming, bidirectional)
        5. Confidence level (high, medium, low as a number between 0 and 1)
        6. Any properties or attributes of the relationship
        
        Format your response as JSON with a "relationships" array containing each relationship.
        Each relationship should have the following structure:
        {
            "source_id": "entity_id_1",
            "target_id": "entity_id_2",
            "type": "relationship_type",
            "direction": "outgoing",
            "confidence": 0.8,
            "properties": {"property1": "value1", "property2": "value2"}
        }
        
        Only infer relationship types specified in the relationship_types list, if provided.
        Otherwise, infer all relationships you can identify.
        """
        
        # Prepare prompt with entity information
        entities_json = json.dumps(entities, indent=2)
        prompt = f"Entities: {entities_json}"
        
        if request.relationship_types:
            relationship_types_str = ", ".join(request.relationship_types)
            prompt = f"Relationship types to infer: {relationship_types_str}\n\n{prompt}"
        
        # Call LLM
        llm_response = await llm_client.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=request.model,
            provider=request.provider,
            response_format="json"
        )
        
        # Parse LLM response
        try:
            # Extract JSON from response
            json_content = llm_response.content
            if isinstance(json_content, str):
                # Find JSON in the string if needed
                if "{" in json_content and "}" in json_content:
                    start = json_content.find("{")
                    end = json_content.rfind("}") + 1
                    json_content = json_content[start:end]
                
                response_data = json.loads(json_content)
            else:
                response_data = json_content
            
            # Create Relationship objects from inferred data
            relationships = []
            for rel_data in response_data.get("relationships", []):
                relationship = Relationship(
                    relationship_type=rel_data.get("type", "generic"),
                    source_id=rel_data.get("source_id", ""),
                    target_id=rel_data.get("target_id", ""),
                    properties=rel_data.get("properties", {}),
                    confidence=rel_data.get("confidence", 0.5),
                    source="llm_inference"
                )
                
                # Set directionality
                if rel_data.get("direction") == "bidirectional":
                    relationship.set_bidirectional(True)
                
                relationships.append(relationship)
            
            return RelationshipInferenceResponse(
                entity_ids=request.entity_ids,
                relationships=relationships,
                raw_inference=response_data
            )
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response as JSON: {e}")
            logger.debug(f"Raw response: {llm_response.content}")
            raise HTTPException(status_code=500, detail="Failed to parse relationship inference response")
    
    except Exception as e:
        logger.error(f"Error inferring relationships: {e}")
        raise HTTPException(status_code=500, detail=f"Error inferring relationships: {str(e)}")

@router.post("/explain/{entity_id}")
async def explain_entity(entity_id: str, model: str = None, provider: str = None):
    """
    Generate an explanation of an entity using the LLM.
    
    This endpoint uses the LLM to generate a comprehensive explanation of the specified entity.
    """
    engine = await get_knowledge_engine()
    
    try:
        # Get the entity
        entity = await engine.get_entity(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity with ID {entity_id} not found")
        
        # Get relationships for context
        relationships = await engine.get_entity_relationships(entity_id, direction="both")
        
        # Prepare context for LLM
        context = {
            "entity": entity.to_dict(),
            "relationships": [
                {
                    "relationship": rel.to_dict(),
                    "connected_entity": connected.to_dict()
                }
                for rel, connected in relationships
            ]
        }
        
        # Construct system prompt
        system_prompt = """
        You are a knowledge graph analysis assistant.
        Generate an explanation of the provided entity based on its properties and relationships.
        
        Your explanation should include:
        1. A clear description of what the entity is
        2. Analysis of its key properties and attributes
        3. Discussion of its relationships with other entities
        4. Any insights or implications that can be derived from the knowledge graph
        
        Keep your explanation concise, factual, and based only on the provided information.
        If certain information is missing, acknowledge the gaps rather than making assumptions.
        """
        
        # Prepare prompt
        context_json = json.dumps(context, indent=2)
        prompt = f"Generate an explanation for entity: {entity.name} (ID: {entity.entity_id})\n\nContext: {context_json}"
        
        # Call LLM
        llm_response = await llm_client.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            provider=provider
        )
        
        return {
            "entity_id": entity_id,
            "entity_name": entity.name,
            "entity_type": entity.entity_type,
            "explanation": llm_response.content
        }
    
    except Exception as e:
        logger.error(f"Error explaining entity: {e}")
        raise HTTPException(status_code=500, detail=f"Error explaining entity: {str(e)}")

@router.post("/query/translate")
async def translate_query(query: str, model: str = None, provider: str = None):
    """
    Translate a natural language query to a graph query language (Cypher).
    
    This endpoint uses the LLM to convert natural language queries into executable graph queries.
    """
    engine = await get_knowledge_engine()
    
    try:
        # Get schema information for context
        schema = await engine.get_schema()
        
        # Construct system prompt
        system_prompt = """
        You are a knowledge graph query translator.
        Translate the natural language query into a Cypher query for Neo4j.
        
        Use the provided graph schema to ensure your query uses correct entity types,
        relationship types, and property names.
        
        Format your response as JSON with:
        1. cypher_query: The translated Cypher query
        2. parameters: Any parameters for the query
        3. explanation: Brief explanation of what the query does
        """
        
        # Prepare prompt
        schema_json = json.dumps(schema, indent=2)
        prompt = f"Natural language query: {query}\n\nGraph schema: {schema_json}"
        
        # Call LLM
        llm_response = await llm_client.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            provider=provider,
            response_format="json"
        )
        
        # Parse LLM response
        try:
            # Extract JSON from response
            json_content = llm_response.content
            if isinstance(json_content, str):
                # Find JSON in the string if needed
                if "{" in json_content and "}" in json_content:
                    start = json_content.find("{")
                    end = json_content.rfind("}") + 1
                    json_content = json_content[start:end]
                
                response_data = json.loads(json_content)
            else:
                response_data = json_content
            
            return {
                "natural_query": query,
                "cypher_query": response_data.get("cypher_query", ""),
                "parameters": response_data.get("parameters", {}),
                "explanation": response_data.get("explanation", "")
            }
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response as JSON: {e}")
            logger.debug(f"Raw response: {llm_response.content}")
            raise HTTPException(status_code=500, detail="Failed to parse query translation response")
    
    except Exception as e:
        logger.error(f"Error translating query: {e}")
        raise HTTPException(status_code=500, detail=f"Error translating query: {str(e)}")