"""
Personal AI OS - Rules API Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class RuleBase(BaseModel):
    """Base schema for rule data"""
    content: str = Field(..., description="Rule content")
    category: str = Field(..., description="Category: style, tone, formatting, logic, safety")


class RuleCreate(RuleBase):
    """Schema for creating a rule manually"""
    user_id: str = Field(..., description="External user ID")


class RuleUpdate(BaseModel):
    """Schema for updating a rule"""
    content: Optional[str] = Field(None, description="New content")
    category: Optional[str] = Field(None, description="New category")
    status: Optional[str] = Field(None, description="New status: active, archived, disabled")


class RuleResponse(BaseModel):
    """Response schema for a single rule"""
    id: str
    content: str
    original_correction: Optional[str]
    category: str
    confidence: float
    times_applied: int
    times_reinforced: int
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]
    last_applied_at: Optional[str]


class RulesListResponse(BaseModel):
    """Response schema for listing rules"""
    rules: List[RuleResponse]
    total: int
    active: int
    archived: int
    disabled: int


class AuditEventResponse(BaseModel):
    """Response schema for audit log event"""
    id: str
    rule_id: Optional[str]
    event_type: str
    event_data: dict
    created_at: str


class AuditLogResponse(BaseModel):
    """Response schema for audit log listing"""
    events: List[AuditEventResponse]
    total: int
