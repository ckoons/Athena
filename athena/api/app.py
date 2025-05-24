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

# Add shared utils to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../shared/utils')))
try:
    from health_check import create_health_response
    from hermes_registration import HermesRegistration, heartbeat_loop
except ImportError as e:
    logger.warning(f"Could not import shared utils: {e}")
    create_health_response = None
    HermesRegistration = None

from .endpoints.knowledge_graph import router as knowledge_router
from .endpoints.entities import router as entities_router
from .endpoints.query import router as query_router
from .endpoints.visualization import router as visualization_router
from .endpoints.llm_integration import router as llm_router
from .endpoints.mcp import mcp_router
from ..core.engine import get_knowledge_engine

logger = logging.getLogger("athena.api")

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
    engine = await get_knowledge_engine()
    status = await engine.get_status()
    
    health_status = "healthy" if status["status"] == "initialized" else "unhealthy"
    
    # Use standardized health response if available
    if create_health_response:
        return create_health_response(
            component_name="athena",
            port=8005,
            version="1.0.0",
            status=health_status,
            registered=is_registered_with_hermes,
            details=status
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
    
    try:
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
                port=8005,
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

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown knowledge engine on application shutdown."""
    global heartbeat_task
    
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
    
    try:
        engine = await get_knowledge_engine()
        if engine.is_initialized:
            await engine.shutdown()
    except Exception as e:
        logger.error(f"Error shutting down knowledge engine: {e}")