"""
Personal AI OS - Analytics API Schemas
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class DailyActivity(BaseModel):
    """Single day activity data point."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    messages: int = Field(0, description="Number of messages on this day")
    corrections: int = Field(0, description="Number of corrections on this day")
    rules_created: int = Field(0, description="Number of rules created on this day")


class CategoryBreakdown(BaseModel):
    """Rule count by category."""
    category: str
    count: int
    percentage: float


class AnalyticsResponse(BaseModel):
    """Response schema for GET /analytics"""
    # Totals
    total_conversations: int = Field(0, description="Total unique conversations")
    total_messages: int = Field(0, description="Total interactions (user + AI pairs)")
    total_rules: int = Field(0, description="Total rules created")
    active_rules: int = Field(0, description="Currently active rules")
    total_corrections: int = Field(0, description="Total corrections made")

    # Rates
    correction_rate: float = Field(0.0, description="Percentage of messages that were corrected")
    avg_rules_per_chat: float = Field(0.0, description="Average rules applied per message")
    avg_confidence: float = Field(0.0, description="Average confidence of active rules")

    # Time series (last 30 days)
    daily_activity: List[DailyActivity] = Field(default_factory=list, description="Daily activity for last 30 days")

    # Breakdowns
    category_breakdown: List[CategoryBreakdown] = Field(default_factory=list, description="Rules by category")

    # Streaks
    most_applied_rule: Optional[str] = Field(None, description="Content of the most-applied rule")
    most_applied_count: int = Field(0, description="Times the most-applied rule was used")
