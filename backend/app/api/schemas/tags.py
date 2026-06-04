"""
Personal AI OS - Tag Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class TagCreateRequest(BaseModel):
    """Request body for creating a tag."""
    user_id: str = Field(..., description="External user ID")
    name: str = Field(..., min_length=1, max_length=100, description="Tag name")
    color: str = Field(default="#6366f1", description="Hex color code (e.g., #6366f1)")


class TagUpdateRequest(BaseModel):
    """Request body for updating a tag."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = None


class TagResponse(BaseModel):
    """Response for a single tag."""
    id: str
    user_id: str
    name: str
    color: str
    created_at: Optional[str] = None
    rule_count: Optional[int] = None


class TagListResponse(BaseModel):
    """Response for listing tags."""
    tags: List[TagResponse]
    total: int


class TagRuleRequest(BaseModel):
    """Request body for tagging/untagging a rule."""
    tag_ids: List[str] = Field(..., description="List of tag UUIDs")


class BulkTagRequest(BaseModel):
    """Request body for bulk tagging."""
    rule_ids: List[str] = Field(..., description="List of rule UUIDs to tag")
    tag_ids: List[str] = Field(..., description="List of tag UUIDs to apply")


class BulkTagResponse(BaseModel):
    """Response for bulk tagging."""
    rules_tagged: int
    total_rules: int
    total_tags: int


class RuleWithTagsResponse(BaseModel):
    """Minimal rule response with tag info."""
    id: str
    content: str
    category: str
    confidence: float
    status: str
