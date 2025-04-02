"""
In-Memory Graph Adapter for Athena

Provides a simple in-memory implementation of the graph database interface
with file-based persistence.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from pathlib import Path
import networkx as nx

from ..entity import Entity
from ..relationship import Relationship

logger = logging.getLogger("athena.graph.memory_adapter")

class MemoryAdapter:
    """
    In-memory graph database adapter using NetworkX.
    
    Provides a simple implementation of the graph database interface
    with optional file persistence for testing and development.
    """
    
    def __init__(self, data_path: str, **kwargs):
        """
        Initialize the memory adapter.
        
        Args:
            data_path: Path to store persistence files
            **kwargs: Additional configuration options
        """
        self.data_path = data_path
        self.entity_file = os.path.join(data_path, "entities.json")
        self.relationship_file = os.path.join(data_path, "relationships.json")
        self.graph = nx.MultiDiGraph()
        self.is_connected = False
        
    async def connect(self) -> bool:
        """
        Connect to the graph database.
        
        Returns:
            True if successful
        """
        logger.info("Connecting to in-memory graph database")
        
        # Ensure data directory exists
        os.makedirs(self.data_path, exist_ok=True)
        
        # Load data from files if they exist
        await self._load_data()
        
        self.is_connected = True
        logger.info("Connected to in-memory graph database")
        return True
        
    async def disconnect(self) -> bool:
        """
        Disconnect from the graph database.
        
        Returns:
            True if successful
        """
        logger.info("Disconnecting from in-memory graph database")
        
        # Save data to files
        await self._save_data()
        
        self.is_connected = False
        logger.info("Disconnected from in-memory graph database")
        return True
        
    async def initialize_schema(self) -> bool:
        """
        Initialize the graph schema.
        
        Returns:
            True if successful
        """
        # No schema initialization needed for in-memory graph
        return True
        
    async def _load_data(self) -> None:
        """Load graph data from persistence files."""
        # Load entities
        if os.path.exists(self.entity_file):
            try:
                with open(self.entity_file, 'r') as f:
                    entities_data = json.load(f)
                    
                for entity_data in entities_data:
                    entity = Entity.from_dict(entity_data)
                    self.graph.add_node(entity.entity_id, entity=entity)
                    
                logger.info(f"Loaded {len(entities_data)} entities from {self.entity_file}")
            except Exception as e:
                logger.error(f"Error loading entities: {e}")
                
        # Load relationships
        if os.path.exists(self.relationship_file):
            try:
                with open(self.relationship_file, 'r') as f:
                    relationships_data = json.load(f)
                    
                for rel_data in relationships_data:
                    relationship = Relationship.from_dict(rel_data)
                    self.graph.add_edge(
                        relationship.source_id,
                        relationship.target_id,
                        key=relationship.relationship_id,
                        relationship=relationship
                    )
                    
                logger.info(f"Loaded {len(relationships_data)} relationships from {self.relationship_file}")
            except Exception as e:
                logger.error(f"Error loading relationships: {e}")
                
    async def _save_data(self) -> None:
        """Save graph data to persistence files."""
        # Save entities
        try:
            entities_data = []
            for node_id in self.graph.nodes():
                entity = self.graph.nodes[node_id].get('entity')
                if entity:
                    entities_data.append(entity.to_dict())
                    
            with open(self.entity_file, 'w') as f:
                json.dump(entities_data, f, indent=2)
                
            logger.info(f"Saved {len(entities_data)} entities to {self.entity_file}")
        except Exception as e:
            logger.error(f"Error saving entities: {e}")
            
        # Save relationships
        try:
            relationships_data = []
            for source_id, target_id, rel_id in self.graph.edges(keys=True):
                relationship = self.graph[source_id][target_id][rel_id].get('relationship')
                if relationship:
                    relationships_data.append(relationship.to_dict())
                    
            with open(self.relationship_file, 'w') as f:
                json.dump(relationships_data, f, indent=2)
                
            logger.info(f"Saved {len(relationships_data)} relationships to {self.relationship_file}")
        except Exception as e:
            logger.error(f"Error saving relationships: {e}")
            
    async def create_entity(self, entity: Entity) -> str:
        """
        Create a new entity.
        
        Args:
            entity: Entity to create
            
        Returns:
            Entity ID
        """
        self.graph.add_node(entity.entity_id, entity=entity)
        return entity.entity_id
        
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Get an entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity or None if not found
        """
        if entity_id in self.graph.nodes:
            return self.graph.nodes[entity_id].get('entity')
        return None
        
    async def update_entity(self, entity: Entity) -> bool:
        """
        Update an entity.
        
        Args:
            entity: Updated entity
            
        Returns:
            True if successful
        """
        if entity.entity_id in self.graph.nodes:
            self.graph.nodes[entity.entity_id]['entity'] = entity
            return True
        return False
        
    async def delete_entity(self, entity_id: str) -> bool:
        """
        Delete an entity.
        
        Args:
            entity_id: Entity ID to delete
            
        Returns:
            True if successful
        """
        if entity_id in self.graph.nodes:
            self.graph.remove_node(entity_id)
            return True
        return False
        
    async def create_relationship(self, relationship: Relationship) -> str:
        """
        Create a new relationship.
        
        Args:
            relationship: Relationship to create
            
        Returns:
            Relationship ID
        """
        self.graph.add_edge(
            relationship.source_id,
            relationship.target_id,
            key=relationship.relationship_id,
            relationship=relationship
        )
        return relationship.relationship_id
        
    async def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """
        Get a relationship by ID.
        
        Args:
            relationship_id: Relationship ID
            
        Returns:
            Relationship or None if not found
        """
        for source_id, target_id, rel_id in self.graph.edges(keys=True):
            if rel_id == relationship_id:
                return self.graph[source_id][target_id][rel_id].get('relationship')
        return None
        
    async def update_relationship(self, relationship: Relationship) -> bool:
        """
        Update a relationship.
        
        Args:
            relationship: Updated relationship
            
        Returns:
            True if successful
        """
        for source_id, target_id, rel_id in self.graph.edges(keys=True):
            if rel_id == relationship.relationship_id:
                self.graph[source_id][target_id][rel_id]['relationship'] = relationship
                return True
        return False
        
    async def delete_relationship(self, relationship_id: str) -> bool:
        """
        Delete a relationship.
        
        Args:
            relationship_id: Relationship ID to delete
            
        Returns:
            True if successful
        """
        for source_id, target_id, rel_id in list(self.graph.edges(keys=True)):
            if rel_id == relationship_id:
                self.graph.remove_edge(source_id, target_id, rel_id)
                return True
        return False
        
    async def search_entities(self, 
                            query: str, 
                            entity_type: Optional[str] = None, 
                            limit: int = 10) -> List[Entity]:
        """
        Search for entities.
        
        Args:
            query: Search query
            entity_type: Optional entity type filter
            limit: Maximum number of results
            
        Returns:
            List of matching entities
        """
        query = query.lower()
        results = []
        
        for node_id in self.graph.nodes():
            entity = self.graph.nodes[node_id].get('entity')
            if not entity:
                continue
                
            # Filter by entity type if specified
            if entity_type and entity.entity_type != entity_type:
                continue
                
            # Check for matches in name or aliases
            if (query in entity.name.lower() or 
                any(query in alias for alias in entity.aliases)):
                results.append(entity)
                
            # Check for matches in properties
            for key, prop in entity.properties.items():
                value = prop.get('value')
                if isinstance(value, str) and query in value.lower():
                    if entity not in results:
                        results.append(entity)
                    break
                    
            if len(results) >= limit:
                break
                
        return results[:limit]
        
    async def get_entity_relationships(self, 
                                    entity_id: str, 
                                    relationship_type: Optional[str] = None,
                                    direction: str = "both") -> List[Tuple[Relationship, Entity]]:
        """
        Get relationships for an entity.
        
        Args:
            entity_id: Entity ID
            relationship_type: Optional relationship type filter
            direction: Relationship direction ('outgoing', 'incoming', or 'both')
            
        Returns:
            List of (relationship, connected entity) tuples
        """
        results = []
        
        # Get outgoing relationships
        if direction in ["outgoing", "both"]:
            for _, target_id, rel_id in self.graph.out_edges(entity_id, keys=True):
                relationship = self.graph[entity_id][target_id][rel_id].get('relationship')
                target_entity = self.graph.nodes[target_id].get('entity')
                
                if not relationship or not target_entity:
                    continue
                    
                if relationship_type and relationship.relationship_type != relationship_type:
                    continue
                    
                results.append((relationship, target_entity))
                
        # Get incoming relationships
        if direction in ["incoming", "both"]:
            for source_id, _, rel_id in self.graph.in_edges(entity_id, keys=True):
                relationship = self.graph[source_id][entity_id][rel_id].get('relationship')
                source_entity = self.graph.nodes[source_id].get('entity')
                
                if not relationship or not source_entity:
                    continue
                    
                if relationship_type and relationship.relationship_type != relationship_type:
                    continue
                    
                results.append((relationship, source_entity))
                
        return results
        
    async def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw query.
        
        Note: For the in-memory adapter, this is a stub that logs the query and returns an empty result.
        
        Args:
            query: Query string
            params: Query parameters
            
        Returns:
            Query results
        """
        logger.warning(f"Raw query execution not supported in memory adapter. Query: {query}")
        return []
        
    async def find_paths(self, 
                      source_id: str, 
                      target_id: str, 
                      max_depth: int = 3) -> List[List[Union[Entity, Relationship]]]:
        """
        Find paths between two entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            max_depth: Maximum path length
            
        Returns:
            List of paths, where each path is a list of alternating Entity and Relationship objects
        """
        if source_id not in self.graph.nodes or target_id not in self.graph.nodes:
            return []
            
        # Use NetworkX to find simple paths
        try:
            # Find all simple paths up to length 2*max_depth (edges + nodes)
            simple_paths = list(nx.all_simple_paths(
                self.graph, source_id, target_id, cutoff=max_depth*2-1
            ))
        except nx.NetworkXNoPath:
            return []
            
        # Convert simple paths to entity/relationship sequences
        result_paths = []
        for path in simple_paths:
            entity_rel_path = []
            
            # Add the source entity
            entity_rel_path.append(self.graph.nodes[path[0]].get('entity'))
            
            # Add relationships and entities along the path
            for i in range(len(path) - 1):
                source = path[i]
                target = path[i + 1]
                
                # Find the relationship between these nodes
                # (there could be multiple, take the first one)
                rel_id = list(self.graph[source][target].keys())[0]
                relationship = self.graph[source][target][rel_id].get('relationship')
                entity_rel_path.append(relationship)
                
                # Add the target entity
                entity_rel_path.append(self.graph.nodes[target].get('entity'))
                
            result_paths.append(entity_rel_path)
            
        return result_paths
        
    async def count_entities(self) -> int:
        """
        Count the number of entities in the graph.
        
        Returns:
            Entity count
        """
        return len(self.graph.nodes)
        
    async def count_relationships(self) -> int:
        """
        Count the number of relationships in the graph.
        
        Returns:
            Relationship count
        """
        return len(self.graph.edges)