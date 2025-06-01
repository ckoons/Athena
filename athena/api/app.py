"""
Athena API Application

Main FastAPI application for Athena's REST API.
Provides comprehensive knowledge graph functionality.
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add Tekton root to path for shared imports
tekton_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if tekton_root not in sys.path:
    sys.path.append(tekton_root)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("athena.api")

# Import shared utils
try:
    from shared.utils.health_check import create_health_response
    from shared.utils.hermes_registration import HermesRegistration, heartbeat_loop
    from shared.utils.logging_setup import setup_component_logger
    from shared.utils.env_config import get_component_config
    from shared.utils.errors import StartupError
except ImportError as e:
    logger.warning(f"Could not import shared utils: {e}")
    create_health_response = None
    HermesRegistration = None
    setup_component_logger = None
    get_component_config = None

# Use shared logger if available
if setup_component_logger:
    logger = setup_component_logger("athena")

from .endpoints.knowledge_graph import router as knowledge_router
from .endpoints.entities import router as entities_router
from .endpoints.query import router as query_router
from .endpoints.visualization import router as visualization_router
from .endpoints.llm_integration import router as llm_router
from .endpoints.mcp import mcp_router
from ..core.engine import get_knowledge_engine

# Global state for Hermes registration
is_registered_with_hermes = False
hermes_registration = None
heartbeat_task = None

# Create FastAPI app
app = FastAPI(
    title="Athena Knowledge Graph API",
    description="API for interacting with the Athena knowledge graph with graph visualization and LLM-enhanced features",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(knowledge_router)
app.include_router(entities_router)
app.include_router(query_router)
app.include_router(visualization_router)
app.include_router(llm_router)
app.include_router(mcp_router)  # Add MCP router

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for API"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected error occurred: {str(exc)}"} 
    )

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Athena Knowledge Graph API",
        "version": "1.0.0",
        "features": [
            "Enhanced entity management",
            "Multiple query modes",
            "Entity merging",
            "Graph and vector integration",
            "FastMCP integration"  # Add FastMCP feature
        ]
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        engine = await get_knowledge_engine()
        if engine:
            status = await engine.get_status()
            health_status = "healthy" if status["status"] == "initialized" else "unhealthy"
            details = status
        else:
            health_status = "starting"
            details = {"status": "starting", "message": "Knowledge engine initializing"}
    except Exception as e:
        logger.warning(f"Knowledge engine not ready: {e}")
        health_status = "starting"
        details = {"status": "starting", "message": "Knowledge engine initializing"}

    # Use standardized health response if available
    if create_health_response:
        return create_health_response(
            component_name="athena",
            port=8005,
            version="1.0.0",
            status=health_status,
            registered=is_registered_with_hermes,
            details=details
        )
    else:
        # Fallback to manual format
        return {
            "status": health_status,
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "component": "athena",
            "port": 8005,
            "registered_with_hermes": is_registered_with_hermes,
            "details": status
        }

@app.on_event("startup")
async def startup_event():
    """Initialize knowledge engine on startup."""
    global is_registered_with_hermes, hermes_registration, heartbeat_task
    
    logger.info("Starting Athena Knowledge Graph API")
    
    try:
        # Get configuration
        if get_component_config:
            config = get_component_config()
            port = config.athena.port
        else:
            port = int(os.environ.get("ATHENA_PORT", 8005))
        
        engine = await get_knowledge_engine()
        if not engine.is_initialized:
            await engine.initialize()
            
        # Log FastMCP initialization
        try:
            from tekton.mcp.fastmcp import (
                mcp_tool,
                mcp_capability,
                MCPClient
            )
            logger.info("FastMCP is available and initialized")
        except ImportError:
            logger.warning("FastMCP is not available - MCP functionality will be limited")
        
        # Register with Hermes if available
        if HermesRegistration:
            hermes_registration = HermesRegistration()
            is_registered_with_hermes = await hermes_registration.register_component(
                component_name="athena",
                port=port,
                version="1.0.0",
                capabilities=[
                    "knowledge_graph_management",
                    "entity_relationship_tracking",
                    "semantic_search",
                    "graph_visualization",
                    "llm_enhanced_analysis"
                ],
                metadata={
                    "graph_type": "knowledge",
                    "storage": "in-memory"
                }
            )
            
            # Start heartbeat task if registered
            if is_registered_with_hermes:
                heartbeat_task = asyncio.create_task(
                    heartbeat_loop(hermes_registration, "athena", interval=30)
                )
                logger.info("Started Hermes heartbeat task")
                
    except Exception as e:
        logger.error(f"Error initializing knowledge engine: {e}")
        if StartupError:
            raise StartupError(str(e), "athena", "INIT_FAILED")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown knowledge engine on application shutdown."""
    global heartbeat_task
    
    logger.info("Shutting down Athena Knowledge Graph API")
    
    # Cancel heartbeat task
    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
    
    # Deregister from Hermes
    if hermes_registration and is_registered_with_hermes:
        await hermes_registration.deregister("athena")
        logger.info("Deregistered from Hermes")
    
    try:
        engine = await get_knowledge_engine()
        if engine.is_initialized:
            await engine.shutdown()
            logger.info("Knowledge engine shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down knowledge engine: {e}")

if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Athena Knowledge Graph API Server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("ATHENA_PORT", 8005)),
                       help="Port to run the server on")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                       help="Host to bind the server to")
    parser.add_argument("--reload", action="store_true",
                       help="Enable auto-reload for development")
    args = parser.parse_args()

    logger.info(f"Starting Athena server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)