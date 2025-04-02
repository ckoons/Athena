#!/usr/bin/env python3
"""
Registers Athena with the Hermes service registry.

This script registers the Athena knowledge graph service with the Hermes centralized
service registry so other components can discover and use it.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("athena_registration")

# Get the directory where this script is located
script_dir = Path(__file__).parent.absolute()

# Check if we're in a virtual environment
venv_dir = os.path.join(script_dir, "venv")
if os.path.exists(venv_dir):
    # Activate the virtual environment if not already activated
    if not os.environ.get("VIRTUAL_ENV"):
        print(f"Please run this script within the Athena virtual environment:")
        print(f"source {venv_dir}/bin/activate")
        print(f"python {os.path.basename(__file__)}")
        sys.exit(1)

# Find Hermes directory (prioritize environment variable if set)
hermes_dir = os.environ.get("HERMES_DIR")
if not hermes_dir or not os.path.exists(hermes_dir):
    # Try to find Hermes relative to this script
    potential_hermes_dir = os.path.normpath(os.path.join(script_dir, "../Hermes"))
    if os.path.exists(potential_hermes_dir):
        hermes_dir = potential_hermes_dir
    else:
        print(f"Hermes directory not found. Please set the HERMES_DIR environment variable.")
        sys.exit(1)

# Add Hermes to the Python path
sys.path.insert(0, hermes_dir)

# Try to import Hermes modules
try:
    from hermes.core.service_discovery import ServiceRegistry
    from hermes.core.registration.client import RegistrationClient
    logger.info(f"Successfully imported Hermes modules from {hermes_dir}")
except ImportError as e:
    logger.error(f"Error importing Hermes modules: {e}")
    logger.error(f"Make sure Hermes is properly installed and accessible")
    sys.exit(1)

async def register_with_hermes():
    """Register Athena services with Hermes."""
    try:
        # Initialize the service registry
        registry = ServiceRegistry()
        await registry.start()
        
        # Register the knowledge graph service
        success = await registry.register(
            service_id="athena-knowledge-graph",
            name="Athena Knowledge Graph",
            version="0.1.0",
            endpoint="http://localhost:5600",  # Default endpoint for Athena API
            capabilities=[
                "knowledge_graph", 
                "entity_management", 
                "relationship_management", 
                "path_finding",
                "fact_verification"
            ],
            metadata={
                "component": "athena",
                "description": "Knowledge graph component of Tekton",
                "adapter": "neo4j" if os.environ.get("ATHENA_USE_NEO4J") else "memory"
            }
        )
        
        if success:
            logger.info("Registered Athena Knowledge Graph with Hermes service registry")
        else:
            logger.error("Failed to register Athena Knowledge Graph")
            return False
        
        # Register the entity service specifically
        success = await registry.register(
            service_id="athena-entity",
            name="Athena Entity Service",
            version="0.1.0",
            endpoint="http://localhost:5600/entity",
            capabilities=["entity_management", "fact_storage"],
            metadata={
                "component": "athena",
                "description": "Entity management service"
            }
        )
        
        if success:
            logger.info("Registered Athena Entity Service with Hermes service registry")
        else:
            logger.error("Failed to register Athena Entity Service")
            return False
            
        await registry.stop()
        logger.info("Registration with Hermes completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error during Hermes registration: {e}")
        return False

# Main execution
if __name__ == "__main__":
    logger.info("Registering Athena with Hermes service registry...")
    success = asyncio.run(register_with_hermes())
    sys.exit(0 if success else 1)
