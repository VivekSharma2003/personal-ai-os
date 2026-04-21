"""
Personal AI OS - Conversation Summarizer API Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    """Request schema for POST /summarize"""
    user_id: str = Field(..., description="External user ID")
    conversation_id: str = Field(..., description="Conversation ID to summarize")
    length: str = Field("brief", description="Summary length: 'brief' or 'detailed'")


class KeyTopic(BaseModel):
    """A key topic extracted from the conversation."""
    topic: str = Field(..., description="Topic name")
    relevance: float = Field(0.0, description="Relevance score 0-1")


class SummaryResponse(BaseModel):
    """Response schema for POST /summarize"""
    conversation_id: str = Field(..., description="The summarized conversation ID")
    summary: str = Field(..., description="The generated summary text")
    key_topics: List[str] = Field(default_factory=list, description="Key topics discussed")
    action_items: List[str] = Field(default_factory=list, description="Action items identified")
    message_count: int = Field(0, description="Number of messages in the conversation")
    duration_text: str = Field("", description="Human-readable duration of the conversation")
    rules_applied_count: int = Field(0, description="Total rules applied during this conversation")
    corrections_count: int = Field(0, description="Number of corrections in this conversation")
