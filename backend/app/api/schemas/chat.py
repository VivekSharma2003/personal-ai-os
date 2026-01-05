"""
Personal AI OS - Chat API Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request schema for POST /chat"""
    user_id: str = Field(..., description="External user ID")
    message: str = Field(..., description="User message", min_length=1, max_length=10000)
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")


class ChatResponse(BaseModel):
    """Response schema for POST /chat"""
    response: str = Field(..., description="AI response")
    rules_applied: int = Field(..., description="Number of rules applied")
    interaction_id: str = Field(..., description="Interaction ID for feedback")


class StreamChatResponse(BaseModel):
    """Streaming response chunk"""
    chunk: str
    done: bool = False
