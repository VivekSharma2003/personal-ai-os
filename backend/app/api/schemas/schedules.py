"""
Personal AI OS - Schedule Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ScheduleCreateRequest(BaseModel):
    """Request body for creating a rule schedule."""
    schedule_type: str = Field(..., description="one_time or recurring")
    start_time: Optional[datetime] = Field(None, description="Start of one-time window (ISO 8601)")
    end_time: Optional[datetime] = Field(None, description="End of one-time window (ISO 8601)")
    cron_expression: Optional[str] = Field(
        None,
        description="Daily time window in HH:MM-HH:MM format for recurring schedules"
    )
    timezone: str = Field(default="UTC", description="IANA timezone (e.g., Asia/Kolkata)")
    active_days: str = Field(
        default="127",
        description="Bitmask for active days: Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32, Sun=64. 127=all, 31=weekdays"
    )
    description: Optional[str] = Field(None, description="Human-readable description")


class ScheduleResponse(BaseModel):
    """Response for a single schedule."""
    id: str
    rule_id: str
    schedule_type: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: str
    active_days: str
    is_active: bool
    description: Optional[str] = None
    created_at: Optional[str] = None


class ScheduleListResponse(BaseModel):
    """Response for listing schedules."""
    schedules: List[ScheduleResponse]
    total: int
    rule_id: str
