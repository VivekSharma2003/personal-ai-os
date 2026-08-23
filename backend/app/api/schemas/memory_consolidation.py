"""
Personal AI OS - Episodic Memory Schemas
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class MemoryConsolidationRequest(BaseModel):
    """Request to trigger memory consolidation."""
    thread_id: Optional[str] = Field(None, description="Optional specific thread to consolidate")
    days_old: Optional[int] = Field(30, description="Consolidate threads older than this many days")


class MemoryConsolidationResponse(BaseModel):
    """Response after triggering memory consolidation."""
    status: str
    memories_created: int
    threads_processed: int


class EpisodicMemoryResponse(BaseModel):
    """Response schema for an episodic memory record."""
    id: UUID
    user_id: UUID
    summary: str
    key_takeaways: List[str]
    interaction_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MemorySearchResponse(BaseModel):
    """Response schema for searching memories."""
    results: List[EpisodicMemoryResponse]
    query: str
