"""
Personal AI OS - Lifecycle Schemas

Pydantic schemas for rule lifecycle management.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class LifecycleEventResponse(BaseModel):
    """Single lifecycle event."""
    event_type: str
    rule_id: Optional[str] = None
    details: Optional[str] = None
    created_at: Optional[str] = None


class StaleRuleResponse(BaseModel):
    """A rule flagged as stale."""
    id: str
    content: str
    category: str
    confidence: float
    days_inactive: int
    reason: str
    status: str
    created_at: Optional[str] = None


class LifecycleReportResponse(BaseModel):
    """User-wide lifecycle analytics."""
    status_counts: Dict[str, int]
    total_rules: int
    avg_age_days: float
    at_risk_count: int
    recent_lifecycle_events: List[LifecycleEventResponse]


class AutoArchiveResponse(BaseModel):
    """Result of auto-archive operation."""
    archived_count: int
    archived_rule_ids: List[str] = []
    scanned_stale: int = 0
    skipped: bool = False
    reason: Optional[str] = None
