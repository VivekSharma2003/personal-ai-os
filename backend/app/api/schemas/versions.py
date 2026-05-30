"""
Personal AI OS - Version API Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class VersionResponse(BaseModel):
    """Response schema for a single rule version."""
    id: str
    rule_id: str
    version_number: int
    content: str
    category: str
    confidence: float
    status: str
    changed_by: str
    change_reason: Optional[str]
    created_at: Optional[str]


class VersionHistoryResponse(BaseModel):
    """Response schema for version history."""
    rule_id: str
    versions: List[VersionResponse]
    total: int


class RollbackRequest(BaseModel):
    """Request schema for rolling back a rule."""
    version_number: int = Field(..., description="Version number to roll back to")


class DiffChange(BaseModel):
    """A single field change in a diff."""
    field: str
    from_value: Optional[str] = Field(None, alias="from")
    to_value: Optional[str] = Field(None, alias="to")

    class Config:
        populate_by_name = True


class DiffResponse(BaseModel):
    """Response schema for a version diff."""
    rule_id: str
    version_a: VersionResponse
    version_b: VersionResponse
    content_diff: List[str]
    changes: List[dict]
    has_changes: bool
