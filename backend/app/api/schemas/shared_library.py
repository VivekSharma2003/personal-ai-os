"""
Personal AI OS - Shared Library Schemas

Pydantic schemas for multi-user shared rule library.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class PublishRuleRequest(BaseModel):
    """Request to publish a rule to the shared library."""
    rule_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    visibility: str = Field(default="public", pattern="^(public|unlisted)$")


class SharedRuleResponse(BaseModel):
    """Single shared rule."""
    id: str
    author_user_id: str
    source_rule_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    content: str
    category: str
    install_count: int
    avg_rating: float
    rating_count: int
    visibility: str
    created_at: Optional[str] = None


class SharedLibraryListResponse(BaseModel):
    """Paginated shared library listing."""
    total: int
    limit: int
    offset: int
    sort_by: str
    rules: List[SharedRuleResponse]


class InstallRuleResponse(BaseModel):
    """Result of installing a shared rule."""
    installed_rule_id: str
    source_shared_rule: SharedRuleResponse


class RateRuleRequest(BaseModel):
    """Request to rate a shared rule."""
    rating: int = Field(..., ge=1, le=5)


class RateRuleResponse(BaseModel):
    """Result of rating a shared rule."""
    shared_rule_id: str
    new_avg_rating: float
    total_ratings: int
