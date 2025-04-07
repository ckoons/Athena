# LightRAG Integration in Athena

This document describes the integration of features from the LightRAG project into the Athena component of Tekton.

## Overview

LightRAG is a simple and fast Retrieval-Augmented Generation system that offers a sophisticated approach to knowledge graph integration with vector retrieval. By integrating key features from LightRAG, Athena now offers enhanced capabilities for knowledge management and retrieval.

## Integrated Features

### 1. Multiple Query Modes

Athena now supports five distinct query modes inspired by LightRAG:

- **Naive Mode**: Simple keyword-based search without complex knowledge graph integration
- **Local Mode**: Entity-focused retrieval that prioritizes relevant entities and their properties
- **Global Mode**: Relationship-focused retrieval for understanding connections between entities
- **Hybrid Mode**: Combined entity and relationship retrieval for a balanced approach
- **Mix Mode**: Integrated graph and vector retrieval (most advanced mode)

### 2. Enhanced Entity Management

The entity management system has been expanded with features from LightRAG:

- **Entity Merging**: Combine multiple entities with configurable merging strategies
- **Enhanced Metadata**: Support for rich metadata, aliases, and source tracking
- **Relationship Migration**: Automatic relationship handling during entity operations
- **Duplicate Detection**: Tools for finding and resolving duplicate entities

### 3. Storage Interfaces

Standardized storage interfaces allow for flexible backend selection:

- **Vector Storage**: Support for various vector databases (FAISS, Milvus, ChromaDB, etc.)
- **Graph Storage**: Support for different graph databases (Neo4j, NetworkX, PostgreSQL/AGE)
- **Key-Value Storage**: Flexible options for document and metadata storage

### 4. Hardware-Aware Optimization

The system now selects optimal storage implementations based on available hardware:

- **Apple Silicon**: Defaults to Qdrant for vector storage
- **NVIDIA GPUs**: Uses GPU-optimized FAISS
- **Other Platforms**: Falls back to CPU-optimized implementations

## API Endpoints

### Query Endpoints

```
POST /query
```

Execute a query using any of the supported retrieval modes.

**Parameters:**
- `question`: The query text
- `mode`: Retrieval mode (`naive`, `local`, `global`, `hybrid`, or `mix`)
- `max_results`: Maximum number of results to return
- Various other parameters to control the retrieval behavior

**Example:**

```json
{
  "question": "What are the relationships between AI technologies?",
  "mode": "global",
  "max_results": 10,
  "relationship_depth": 2
}
```

### Entity Management Endpoints

```
POST /entities/merge
```

Merge multiple entities into a single entity.

**Parameters:**
- `source_entities`: List of entity IDs or names to merge
- `target_entity_name`: Name for the merged entity
- `target_entity_type`: Optional type for the merged entity
- `merge_strategies`: Optional field-specific merge strategies

**Example:**

```json
{
  "source_entities": ["AI", "Artificial Intelligence", "Machine Intelligence"],
  "target_entity_name": "Artificial Intelligence",
  "target_entity_type": "Technology",
  "merge_strategies": {
    "properties": "join_properties",
    "aliases": "join_unique",
    "confidence": "max_confidence"
  }
}
```

## Usage Examples

### Query with Different Modes

```python
from tekton.clients import AthenaClient

client = AthenaClient()

# Basic search
naive_results = await client.query("What is machine learning?", mode="naive")

# Entity-focused search
local_results = await client.query("What is machine learning?", mode="local")

# Relationship-focused search
global_results = await client.query("How does machine learning relate to neural networks?", mode="global")

# Comprehensive search
hybrid_results = await client.query("Explain the evolution of machine learning", mode="hybrid")

# Advanced integrated search
mix_results = await client.query("Compare traditional machine learning with deep learning", mode="mix")
```

### Entity Merging

```python
from tekton.clients import AthenaClient

client = AthenaClient()

# Find potential duplicates
duplicates = await client.find_duplicate_entities(entity_type="Person")

# Merge specific entities
merged_entity = await client.merge_entities(
    source_entities=["John Smith", "J. Smith", "Dr. Smith"],
    target_entity_name="John Smith",
    merge_strategies={
        "properties": "join_properties",
        "aliases": "join_unique"
    }
)
```

## Implementation Details

The implementation of these features involved creating:

1. Standardized query parameter models in Tekton core
2. Common storage interfaces for interchangeable backends
3. A storage factory for hardware-aware implementation selection
4. Enhanced entity models with merging capabilities
5. A multi-modal query engine
6. API endpoints exposing the new capabilities
7. Hermes integration for cross-component discovery

## Future Improvements

Potential future improvements include:

1. Implementing all backend storage adapters
2. Adding visualization capabilities for knowledge graphs
3. Enhancing entity merging with AI-assisted suggestions
4. Implementing more sophisticated mix-mode search algorithms
5. Adding document ingestion pipeline from LightRAG