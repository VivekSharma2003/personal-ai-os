"""
Personal AI OS - Rule Suggestions API Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class RuleSuggestion(BaseModel):
    """A suggested rule derived from interaction patterns."""
    content: str = Field(..., description="The suggested rule content")
    category: str = Field(..., description="Suggested category (style, tone, formatting, logic, safety)")
    confidence: float = Field(..., description="Confidence score 0-1 for this suggestion")
    reason: str = Field(..., description="Why this rule is being suggested")
    example_interaction: Optional[str] = Field(None, description="Example interaction that led to this suggestion")
    times_observed: int = Field(1, description="Number of interactions supporting this pattern")


class SuggestionsResponse(BaseModel):
    """Response schema for GET /suggestions"""
    suggestions: List[RuleSuggestion] = Field(default_factory=list, description="List of rule suggestions")
    total: int = Field(0, description="Number of suggestions")
    interactions_analyzed: int = Field(0, description="Number of recent interactions analyzed")
