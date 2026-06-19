"""
Personal AI OS - Retention Policy Schemas
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RetentionPolicyResponse(BaseModel):
    """A single retention policy."""
    id: Optional[str] = None
    user_id: str
    resource_type: str
    retention_days: int = Field(description="Days to retain (0 = forever)")
    is_custom: bool = Field(description="True if user-overridden, False if system default")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RetentionPoliciesResponse(BaseModel):
    """All retention policies for a user."""
    policies: List[RetentionPolicyResponse]


class RetentionPolicySetRequest(BaseModel):
    """Request to set a retention policy."""
    user_id: str = Field(..., description="External user ID")
    resource_type: str = Field(
        ..., description="Resource type: 'interactions', 'audit_logs', 'conversations'"
    )
    retention_days: int = Field(
        ..., ge=0, le=3650, description="Days to retain (0 = forever, max 10 years)"
    )


class CleanupPreviewResponse(BaseModel):
    """Preview of what a cleanup would delete."""
    would_delete: Dict[str, int] = Field(
        description="Records that would be deleted per resource type"
    )


class CleanupResultResponse(BaseModel):
    """Result of a cleanup execution."""
    deleted: Dict[str, int] = Field(
        description="Records deleted per resource type"
    )


class StorageStatsResource(BaseModel):
    """Storage stats for a single resource type."""
    total_records: int
    oldest_record: Optional[str] = None
    newest_record: Optional[str] = None


class StorageStatsResponse(BaseModel):
    """Storage usage stats for all resource types."""
    stats: Dict[str, StorageStatsResource]
