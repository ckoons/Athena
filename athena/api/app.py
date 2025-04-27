"""
Athena API Application

Main FastAPI application for Athena's REST API.
Provides comprehensive knowledge graph functionality.
"""

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .endpoints.knowledge_graph import router as knowledge_router
from .endpoints.entities import router as entities_router
from .endpoints.query import router as query_router
from .endpoints.visualization import router as visualization_router
from .endpoints.llm_integration import router as llm_router
from ..core.engine import get_knowledge_engine

logger = logging.getLogger("athena.api")

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
            "Graph and vector integration"
        ]
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    engine = await get_knowledge_engine()
    status = await engine.get_status()
    
    if status["status"] == "initialized":
        return {
            "status": "healthy",
            "details": status
        }
    else:
        return {
            "status": "unhealthy",
            "details": status
        }

@app.on_event("startup")
async def startup_event():
    """Initialize knowledge engine on startup."""
    try:
        engine = await get_knowledge_engine()
        if not engine.is_initialized:
            await engine.initialize()
    except Exception as e:
        logger.error(f"Error initializing knowledge engine: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown knowledge engine on application shutdown."""
    try:
        engine = await get_knowledge_engine()
        if engine.is_initialized:
            await engine.shutdown()
    except Exception as e:
        logger.error(f"Error shutting down knowledge engine: {e}")