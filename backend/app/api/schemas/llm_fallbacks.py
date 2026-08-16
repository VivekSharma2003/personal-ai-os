"""
Personal AI OS - LLM Fallback Policy Schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class LLMFallbackPolicyBase(BaseModel):
    """Base schema for LLM Fallback Policy."""
    primary_provider: str = Field(..., description="Primary LLM provider")
    primary_model: str = Field(..., description="Primary LLM model")
    fallback_provider: str = Field(..., description="Fallback LLM provider")
    fallback_model: str = Field(..., description="Fallback LLM model")
    max_retries: Optional[int] = Field(3, description="Maximum number of retries before falling back")
    backoff_factor: Optional[float] = Field(2.0, description="Multiplier for exponential backoff")
    is_active: Optional[bool] = Field(True, description="Whether this fallback policy is active")


class LLMFallbackPolicyCreate(LLMFallbackPolicyBase):
    """Schema for creating a new LLM Fallback Policy."""
    user_id: UUID = Field(..., description="User ID for this policy")


class LLMFallbackPolicyUpdate(BaseModel):
    """Schema for updating an LLM Fallback Policy."""
    primary_provider: Optional[str] = None
    primary_model: Optional[str] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    max_retries: Optional[int] = None
    backoff_factor: Optional[float] = None
    is_active: Optional[bool] = None


class LLMFallbackPolicyResponse(LLMFallbackPolicyBase):
    """Schema for returning an LLM Fallback Policy."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
