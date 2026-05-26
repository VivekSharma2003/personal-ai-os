"""
Personal AI OS - Conversation API Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    """Request schema for creating a conversation."""
    user_id: str = Field(..., description="External user ID")
    title: Optional[str] = Field(None, description="Conversation title")
    description: Optional[str] = Field(None, description="Description")


class ConversationUpdateRequest(BaseModel):
    """Request schema for updating a conversation."""
    title: Optional[str] = None
    description: Optional[str] = None


class ForkRequest(BaseModel):
    """Request schema for forking a conversation."""
    user_id: str = Field(..., description="External user ID")
    at_interaction_id: str = Field(..., description="Interaction ID to fork at")
    title: Optional[str] = Field(None, description="Title for the forked conversation")


class ConversationResponse(BaseModel):
    """Response schema for a conversation."""
    id: str
    title: str
    description: Optional[str]
    parent_id: Optional[str]
    forked_at_interaction_id: Optional[str]
    is_archived: bool
    is_pinned: bool
    message_count: Optional[int] = 0
    created_at: Optional[str]
    updated_at: Optional[str]


class ConversationsListResponse(BaseModel):
    """Response schema for listing conversations."""
    conversations: List[ConversationResponse]
    total: int


class ConversationTreeResponse(BaseModel):
    """Response schema for a conversation tree."""
    id: str
    title: str
    description: Optional[str]
    parent_id: Optional[str]
    is_archived: bool
    is_pinned: bool
    message_count: int = 0
    created_at: Optional[str]
    updated_at: Optional[str]
    forks: List["ConversationTreeResponse"] = []


# Allow self-referencing
ConversationTreeResponse.model_rebuild()
