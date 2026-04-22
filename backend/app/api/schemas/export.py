"""
Personal AI OS - Export & Backup API Schemas
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ExportMetadata(BaseModel):
    """Metadata about the export."""
    exported_at: str = Field(..., description="ISO timestamp of export")
    version: str = Field("1.0.0", description="Export format version")
    user_id: str = Field(..., description="External user ID")
    total_rules: int = Field(0)
    total_interactions: int = Field(0)
    total_audit_events: int = Field(0)


class ExportedRule(BaseModel):
    """A rule in the export."""
    id: str
    content: str
    original_correction: Optional[str] = None
    category: str
    confidence: float
    times_applied: int
    times_reinforced: int
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_applied_at: Optional[str] = None


class ExportedInteraction(BaseModel):
    """An interaction in the export."""
    id: str
    conversation_id: Optional[str] = None
    user_message: str
    assistant_response: str
    rules_applied: List[str] = Field(default_factory=list)
    was_corrected: bool = False
    correction_text: Optional[str] = None
    created_at: Optional[str] = None


class ExportedAuditEvent(BaseModel):
    """An audit event in the export."""
    id: str
    rule_id: Optional[str] = None
    event_type: str
    event_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class ExportResponse(BaseModel):
    """Response schema for GET /export"""
    metadata: ExportMetadata
    rules: List[ExportedRule] = Field(default_factory=list)
    interactions: List[ExportedInteraction] = Field(default_factory=list)
    audit_events: List[ExportedAuditEvent] = Field(default_factory=list)
