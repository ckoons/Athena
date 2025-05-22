"""
Data models for Athena.
"""

from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field

from athena.core.entity import Entity


class EntityModel(BaseModel):
    """Pydantic model wrapper for Entity class"""
    
    entity: Entity = Field(...)
    
    class Config:
        """Model configuration."""
        arbitrary_types_allowed = True