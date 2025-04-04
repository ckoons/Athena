"""
Athena API Application

Main FastAPI application for Athena's REST API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .endpoints.knowledge_graph import router as knowledge_router
from ..core.engine import get_knowledge_engine

# Create FastAPI app
app = FastAPI(
    title="Athena Knowledge Graph API",
    description="API for interacting with the Athena knowledge graph",
    version="0.1.0",
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

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to Athena Knowledge Graph API"}

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
        print(f"Error initializing knowledge engine: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown knowledge engine on application shutdown."""
    try:
        engine = await get_knowledge_engine()
        if engine.is_initialized:
            await engine.shutdown()
    except Exception as e:
        print(f"Error shutting down knowledge engine: {e}")