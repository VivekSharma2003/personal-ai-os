"""
Personal AI OS - Conflict API Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ConflictResponse(BaseModel):
    """Response schema for a single conflict."""
    id: str
    rule_a_id: str
    rule_b_id: str
    rule_a_content: Optional[str]
    rule_b_content: Optional[str]
    explanation: str
    severity: float
    suggested_resolution: str
    status: str
    resolved_at: Optional[str]
    resolution_applied: Optional[str]
    created_at: Optional[str]


class ConflictsListResponse(BaseModel):
    """Response schema for listing conflicts."""
    conflicts: List[ConflictResponse]
    total: int
    active: int


class ResolveConflictRequest(BaseModel):
    """Request schema for resolving a conflict."""
    resolution: str = Field(
        ...,
        description="Resolution strategy: keep_both, keep_newer, keep_older, merge, disable_one"
    )
    merged_content: Optional[str] = Field(None, description="Merged rule text (required for 'merge' strategy)")
    disable_rule_id: Optional[str] = Field(None, description="Rule ID to disable (required for 'disable_one' strategy)")


class ConflictScanResponse(BaseModel):
    """Response schema for a manual conflict scan."""
    new_conflicts: int
    total_active: int
    message: str
