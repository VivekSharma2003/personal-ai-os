"""
Personal AI OS - Cost Schemas

Pydantic schemas for LLM cost tracking and budget management.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class UsageRecord(BaseModel):
    """Single LLM usage record."""
    id: str
    provider: str
    model: str
    endpoint: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    created_at: Optional[str] = None


class ProviderBreakdown(BaseModel):
    """Cost breakdown by provider."""
    provider: str
    requests: int
    tokens: int
    cost: float


class ModelBreakdown(BaseModel):
    """Cost breakdown by model."""
    provider: str
    model: str
    requests: int
    tokens: int
    cost: float


class EndpointBreakdown(BaseModel):
    """Cost breakdown by endpoint."""
    endpoint: str
    requests: int
    tokens: int
    cost: float


class UsageSummaryResponse(BaseModel):
    """Aggregated usage summary."""
    period: str
    since: str
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost_usd: float
    by_provider: List[ProviderBreakdown]
    by_model: List[ModelBreakdown]


class CostTrendPoint(BaseModel):
    """Single data point in cost trend."""
    date: str
    requests: int
    tokens: int
    cost: float


class CostTrendResponse(BaseModel):
    """Daily cost trend over time."""
    days: int
    trend: List[CostTrendPoint]


class CostBreakdownResponse(BaseModel):
    """Per-endpoint cost breakdown."""
    period: str
    since: str
    by_endpoint: List[EndpointBreakdown]


class BudgetResponse(BaseModel):
    """Budget status and limits."""
    daily_limit_usd: float
    monthly_limit_usd: float
    daily_spend_usd: float
    monthly_spend_usd: float
    daily_remaining_usd: float
    monthly_remaining_usd: float
    daily_exceeded: bool
    monthly_exceeded: bool


class BudgetCheckResponse(BudgetResponse):
    """Budget pre-flight check result."""
    allowed: bool
