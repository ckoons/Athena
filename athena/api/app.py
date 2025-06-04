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
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add Tekton root to path for shared imports
tekton_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if tekton_root not in sys.path:
    sys.path.append(tekton_root)

# Import shared utils
from shared.utils.health_check import create_health_response
from shared.utils.hermes_registration import HermesRegistration, heartbeat_loop
from shared.utils.logging_setup import setup_component_logging as setup_component_logger
from shared.utils.env_config import get_component_config
from shared.utils.errors import StartupError
from shared.utils.startup import component_startup, StartupMetrics
from shared.utils.shutdown import GracefulShutdown
from shared.api import (
    create_standard_routers,
    mount_standard_routers,
    create_ready_endpoint,
    create_discovery_endpoint,
    get_openapi_configuration,
    EndpointInfo
)

# Use shared logger
logger = setup_component_logger("athena")

from .endpoints.knowledge_graph import router as knowledge_router
from .endpoints.entities import router as entities_router
from .endpoints.query import router as query_router
from .endpoints.visualization import router as visualization_router
from .endpoints.llm_integration import router as llm_router
from .endpoints.mcp import mcp_router
from ..core.engine import get_knowledge_engine

# Component configuration
COMPONENT_NAME = "Athena"
COMPONENT_VERSION = "0.1.0"
COMPONENT_DESCRIPTION = "Knowledge Graph System for relationship tracking and semantic search"

# Global state for Hermes registration
is_registered_with_hermes = False
hermes_registration = None
heartbeat_task = None
start_time = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for Athena"""
    global is_registered_with_hermes, hermes_registration, heartbeat_task, start_time
    
    # Track startup time
    import time
    start_time = time.time()
    
    # Startup
    logger.info("Starting Athena Knowledge Graph API")
    
    async def athena_startup():
        """Athena-specific startup logic"""
        try:
            # Get configuration
            config = get_component_config()
            port = config.athena.port if hasattr(config, 'athena') else int(os.environ.get("ATHENA_PORT", 8005))
            
            # Initialize knowledge engine
            engine = await get_knowledge_engine()
            if not engine.is_initialized:
                await engine.initialize()
                logger.info("Knowledge engine initialized successfully")
                
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
            
            # Register with Hermes
            global is_registered_with_hermes, hermes_registration, heartbeat_task
            hermes_registration = HermesRegistration()
            
            logger.info(f"Attempting to register Athena with Hermes on port {port}")
            is_registered_with_hermes = await hermes_registration.register_component(
                component_name="athena",
                port=port,
                version=COMPONENT_VERSION,
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
            
            if is_registered_with_hermes:
                logger.info("Successfully registered with Hermes")
                # Start heartbeat task
                heartbeat_task = asyncio.create_task(
                    heartbeat_loop(hermes_registration, "athena", interval=30)
                )
                logger.info("Started Hermes heartbeat task")
            else:
                logger.warning("Failed to register with Hermes - continuing without registration")
                
        except Exception as e:
            logger.error(f"Error during Athena startup: {e}", exc_info=True)
            raise StartupError(str(e), "athena", "STARTUP_FAILED")
    
    # Execute startup with metrics
    try:
        metrics = await component_startup("athena", athena_startup, timeout=30)
        logger.info(f"Athena started successfully in {metrics.total_time:.2f}s")
    except Exception as e:
        logger.error(f"Failed to start Athena: {e}")
        raise
    
    # Create shutdown handler
    shutdown = GracefulShutdown("athena")
    
    # Register cleanup tasks
    async def cleanup_hermes():
        """Cleanup Hermes registration"""
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if hermes_registration and is_registered_with_hermes:
            await hermes_registration.deregister("athena")
            logger.info("Deregistered from Hermes")
    
    async def cleanup_engine():
        """Cleanup knowledge engine"""
        try:
            engine = await get_knowledge_engine()
            await engine.cleanup()
            logger.info("Knowledge engine cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning up knowledge engine: {e}")
    
    shutdown.register_cleanup(cleanup_hermes)
    shutdown.register_cleanup(cleanup_engine)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Athena Knowledge Graph API")
    await shutdown.shutdown_sequence(timeout=10)
    
    # Socket release delay for macOS
    await asyncio.sleep(0.5)

# Create FastAPI app with standard configuration
app = FastAPI(
    **get_openapi_configuration(
        component_name=COMPONENT_NAME,
        component_version=COMPONENT_VERSION,
        component_description=COMPONENT_DESCRIPTION
    ),
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create standard routers
routers = create_standard_routers(COMPONENT_NAME)

# Add infrastructure endpoints to root router
@routers.root.get("/health")
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

    # Use standardized health response
    return create_health_response(
        component_name="athena",
        port=int(os.environ.get("ATHENA_PORT", 8005)),
        version=COMPONENT_VERSION,
        status=health_status,
        registered=is_registered_with_hermes,
        details=details
    )

# Add ready endpoint
routers.root.add_api_route(
    "/ready",
    create_ready_endpoint(
        component_name=COMPONENT_NAME,
        component_version=COMPONENT_VERSION,
        start_time=start_time or 0,
        readiness_check=lambda: is_registered_with_hermes
    ),
    methods=["GET"]
)

# Add discovery endpoint to v1 router
routers.v1.add_api_route(
    "/discovery",
    create_discovery_endpoint(
        component_name=COMPONENT_NAME,
        component_version=COMPONENT_VERSION,
        component_description=COMPONENT_DESCRIPTION,
        endpoints=[
            EndpointInfo(
                path="/api/v1/knowledge",
                method="GET",
                description="Get knowledge graph overview"
            ),
            EndpointInfo(
                path="/api/v1/entities",
                method="GET",
                description="List all entities"
            ),
            EndpointInfo(
                path="/api/v1/entities",
                method="POST",
                description="Create new entity"
            ),
            EndpointInfo(
                path="/api/v1/query/search",
                method="POST",
                description="Search entities"
            ),
            EndpointInfo(
                path="/api/v1/visualization/graph",
                method="GET",
                description="Get graph visualization data"
            )
        ],
        capabilities=[
            "knowledge_graph_management",
            "entity_relationship_tracking",
            "semantic_search",
            "graph_visualization",
            "llm_enhanced_analysis"
        ],
        dependencies={
            "hermes": "http://localhost:8001",
            "rhetor": "http://localhost:8003"
        },
        metadata={
            "graph_type": "knowledge",
            "storage": "in-memory",
            "documentation": "/api/v1/docs"
        }
    ),
    methods=["GET"]
)

# Include business logic routers under v1
routers.v1.include_router(knowledge_router, prefix="/knowledge", tags=["Knowledge Graph"])
routers.v1.include_router(entities_router, prefix="/entities", tags=["Entities"])
routers.v1.include_router(query_router, prefix="/query", tags=["Query"])
routers.v1.include_router(visualization_router, prefix="/visualization", tags=["Visualization"])
routers.v1.include_router(llm_router, prefix="/llm", tags=["LLM Integration"])

# Mount standard routers
mount_standard_routers(app, routers)

# MCP router remains at its current location (handled in YetAnotherMCP_Sprint)
app.include_router(mcp_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for API"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected error occurred: {str(exc)}"} 
    )

@routers.root.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {COMPONENT_NAME} API",
        "version": COMPONENT_VERSION,
        "features": [
            "Enhanced entity management",
            "Multiple query modes",
            "Entity merging",
            "Graph and vector integration",
            "FastMCP integration"
        ],
        "docs": "/api/v1/docs"
    }


if __name__ == "__main__":
    from shared.utils.socket_server import run_component_server
    
    port = int(os.environ.get("ATHENA_PORT"))
    run_component_server(
        component_name="athena",
        app_module="athena.api.app",
        default_port=port,
        reload=False
    )