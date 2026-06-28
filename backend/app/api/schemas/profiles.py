"""
Personal AI OS - Profile Schemas

Pydantic schemas for prompt profile CRUD.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class CreateProfileRequest(BaseModel):
    """Request to create a prompt profile."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    rule_filter_tags: List[str] = Field(default=[])
    rule_filter_categories: List[str] = Field(default=[])
    system_preamble: str = Field(default="")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32000)
    is_default: bool = False


class UpdateProfileRequest(BaseModel):
    """Request to update a prompt profile."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    rule_filter_tags: Optional[List[str]] = None
    rule_filter_categories: Optional[List[str]] = None
    system_preamble: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32000)
    is_default: Optional[bool] = None


class CloneProfileRequest(BaseModel):
    """Request to clone a profile."""
    new_name: str = Field(..., min_length=1, max_length=255)


class ProfileResponse(BaseModel):
    """Prompt profile details."""
    id: str
    user_id: str
    name: str
    description: str
    rule_filter_tags: List[str]
    rule_filter_categories: List[str]
    system_preamble: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_default: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProfileListResponse(BaseModel):
    """List of profiles."""
    profiles: List[ProfileResponse]
    total: int
