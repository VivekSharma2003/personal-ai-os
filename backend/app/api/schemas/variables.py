"""
Personal AI OS - Variable Schemas

Pydantic schemas for shared variable endpoints.
"""
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class SharedVariableUpsert(BaseModel):
    """Schema to set/update a shared variable value."""
    name: str = Field(..., pattern="^[a-zA-Z0-9_]+$", max_length=100)
    value: str = Field(..., min_length=1)
    description: Optional[str] = Field(default=None, max_length=255)


class SharedVariableResponse(BaseModel):
    """Response schema for a shared variable."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    value: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
