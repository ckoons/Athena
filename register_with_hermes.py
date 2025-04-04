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

# Add Athena to the Python path if not already there
athena_dir = str(Path(__file__).parent)
if athena_dir not in sys.path:
    sys.path.insert(0, athena_dir)

# Try to import Hermes modules
try:
    from hermes.utils.registration_helper import register_component, unregister_component
    logger.info(f"Successfully imported Hermes modules from {hermes_dir}")
except ImportError as e:
    logger.error(f"Error importing Hermes modules: {e}")
    logger.error(f"Make sure Hermes is properly installed and accessible")
    sys.exit(1)

# Import the Athena knowledge adapter
try:
    from athena.integrations.hermes.knowledge_adapter import HermesKnowledgeAdapter
    logger.info("Successfully imported Athena knowledge adapter")
except ImportError as e:
    logger.error(f"Error importing Athena modules: {e}")
    logger.error(f"Make sure Athena is properly installed and accessible")
    sys.exit(1)

async def register_with_hermes():
    """Register Athena services with Hermes."""
    try:
        # Get Hermes URL from environment or use default
        hermes_url = os.environ.get("HERMES_URL", "http://localhost:8000")
        logger.info(f"Using Hermes URL: {hermes_url}")
        
        # Create the adapter
        adapter = HermesKnowledgeAdapter(
            component_id="athena.knowledge",
            hermes_url=hermes_url,
            auto_register=False  # We'll register manually
        )
        
        # Initialize the engine
        await adapter.initialize()
        
        # Register with Hermes
        success = await adapter.register_with_hermes()
        
        if success:
            logger.info("Successfully registered Athena with Hermes")
            
            # Keep the registration alive until interrupted
            try:
                logger.info("Registration active. Press Ctrl+C to unregister and exit...")
                # Run indefinitely until interrupted
                while True:
                    await asyncio.sleep(60)
                    logger.info("Athena registration still active...")
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, unregistering...")
            finally:
                # Unregister from Hermes before exiting
                await adapter.shutdown()
                logger.info("Athena unregistered from Hermes")
            
            return True
        else:
            logger.error("Failed to register Athena with Hermes")
            return False
    except Exception as e:
        logger.error(f"Error during Hermes registration: {e}")
        return False

# Main execution
if __name__ == "__main__":
    logger.info("Registering Athena with Hermes service registry...")
    success = asyncio.run(register_with_hermes())
    sys.exit(0 if success else 1)
