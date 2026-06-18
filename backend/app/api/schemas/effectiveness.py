"""
Personal AI OS - Effectiveness Analytics Schemas
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RuleEffectivenessResponse(BaseModel):
    """Effectiveness detail for a single rule."""
    rule_id: str
    rule_content: str
    category: str
    score: float = Field(ge=0, le=100, description="Effectiveness score 0-100")
    grade: str = Field(description="Letter grade A-F")
    trend: str = Field(description="improving, declining, or stable")
    apply_count: int
    reinforce_count: int
    override_count: int
    reinforce_rate: float = Field(description="Reinforcement rate as percentage")
    override_rate: float = Field(description="Override rate as percentage")
    last_applied: Optional[str] = None
    days_since_applied: Optional[int] = None


class RuleScoredSummary(BaseModel):
    """Short summary of a scored rule."""
    rule_id: str
    content: str
    category: str
    score: float
    grade: str
    apply_count: int
    reinforce_rate: float
    days_since_applied: Optional[int] = None


class CategoryBreakdown(BaseModel):
    """Effectiveness breakdown for a rule category."""
    count: int
    average_score: float


class EffectivenessReportResponse(BaseModel):
    """User-wide effectiveness report."""
    total_rules: int
    average_score: float
    top_rules: List[RuleScoredSummary] = Field(default_factory=list)
    underperforming_rules: List[RuleScoredSummary] = Field(default_factory=list)
    stale_rules: List[RuleScoredSummary] = Field(default_factory=list)
    category_breakdown: Dict[str, CategoryBreakdown] = Field(default_factory=dict)
