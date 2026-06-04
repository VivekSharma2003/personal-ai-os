"""
Personal AI OS - Audit Schemas
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    """Response for a single audit log entry."""
    id: str
    rule_id: Optional[str] = None
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


class AuditListResponse(BaseModel):
    """Paginated response for audit logs."""
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditStatsResponse(BaseModel):
    """Response for audit log statistics."""
    total_events: int
    event_counts: Dict[str, int]
    most_recent: Optional[AuditLogResponse] = None
