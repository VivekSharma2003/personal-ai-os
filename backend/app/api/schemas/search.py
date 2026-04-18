"""
Personal AI OS - Search API Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single search result from interactions."""
    interaction_id: str = Field(..., description="ID of the matching interaction")
    conversation_id: Optional[str] = Field(None, description="Conversation this belongs to")
    user_message: str = Field(..., description="The user's message")
    assistant_response: str = Field(..., description="The AI response")
    snippet: str = Field(..., description="Highlighted snippet of the match")
    relevance_score: float = Field(0.0, description="Relevance score 0-1")
    was_corrected: bool = Field(False, description="Whether this interaction was corrected")
    rules_applied_count: int = Field(0, description="Number of rules applied in this interaction")
    created_at: Optional[str] = Field(None, description="When this interaction occurred")


class SearchResponse(BaseModel):
    """Response schema for GET /search"""
    query: str = Field(..., description="The search query")
    results: List[SearchResult] = Field(default_factory=list, description="Matching results")
    total: int = Field(0, description="Total number of matches")
    page: int = Field(1, description="Current page")
    page_size: int = Field(20, description="Results per page")
