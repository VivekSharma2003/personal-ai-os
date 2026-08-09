"""
Personal AI OS - Rule Model Config Schemas

Pydantic schemas for rule-specific LLM configurations.
"""
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class RuleModelConfigUpsert(BaseModel):
    """Schema for creating or updating a model config override."""
    provider: str = Field(..., pattern="^(openai|gemini|anthropic)$")
    model_name: str = Field(..., min_length=1, max_length=100)
    temperature_override: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens_override: Optional[int] = Field(default=None, ge=1)
    optimized_content: Optional[str] = Field(default=None, min_length=1)


class RuleModelConfigResponse(BaseModel):
    """Schema for a model config override response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: UUID
    provider: str
    model_name: str
    temperature_override: Optional[float] = None
    max_tokens_override: Optional[int] = None
    optimized_content: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
