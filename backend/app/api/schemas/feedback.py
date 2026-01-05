"""
Personal AI OS - Feedback API Schemas
"""
from typing import Optional
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    """Request schema for POST /feedback"""
    interaction_id: str = Field(..., description="ID of the interaction to provide feedback on")
    correction: str = Field(..., description="User's correction or feedback", min_length=1, max_length=2000)


class RuleInfo(BaseModel):
    """Nested schema for rule information"""
    id: str
    content: str
    category: str
    confidence: float
    status: str
    times_applied: int = 0
    times_reinforced: int = 0
    created_at: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response schema for POST /feedback"""
    status: str = Field(..., description="Status: rule_created, rule_reinforced, extraction_failed, error")
    rule: Optional[RuleInfo] = Field(None, description="The created or reinforced rule")
    message: str = Field(..., description="Human-readable message")
