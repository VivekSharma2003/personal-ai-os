"""
Personal AI OS - API Key Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class APIKeyCreateRequest(BaseModel):
    """Request to create a new API key."""
    user_id: str = Field(..., description="External user ID")
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable key name")
    scopes: List[str] = Field(
        default=["*"],
        description="Permission scopes: ['*'] for all, or specific like ['chat', 'rules']",
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=365,
        description="Days until expiry (None = never expires)",
    )


class APIKeyCreateResponse(BaseModel):
    """
    Response after creating an API key.

    WARNING: `raw_key` is returned ONLY at creation time. Store it securely.
    """
    id: str
    name: str
    key_prefix: str
    raw_key: str = Field(description="Full API key — shown only once")
    scopes: List[str]
    expires_at: Optional[str] = None
    created_at: Optional[str] = None


class APIKeyResponse(BaseModel):
    """API key metadata (never includes the raw key)."""
    id: str
    name: str
    key_prefix: str
    scopes: List[str]
    is_active: bool
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    created_at: Optional[str] = None


class APIKeyListResponse(BaseModel):
    """List of API keys for a user."""
    keys: List[APIKeyResponse]
    total: int
