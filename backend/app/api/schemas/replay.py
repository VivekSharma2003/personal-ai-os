"""
Personal AI OS - Replay Schemas

Pydantic schemas for prompt replay and regression testing.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class StartReplayRequest(BaseModel):
    """Request to start a replay run."""
    name: str = Field(..., min_length=1, max_length=255)
    interaction_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific interaction IDs to replay. If omitted, samples recent interactions.",
    )
    sample_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of recent interactions to sample (when interaction_ids is not provided).",
    )


class ReplayRunResponse(BaseModel):
    """Replay run summary."""
    id: str
    user_id: str
    name: str
    status: str
    total_interactions: int
    completed: int
    regressions_found: int
    improvements_found: int
    unchanged_count: int
    progress_pct: float
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class ReplayRunListResponse(BaseModel):
    """Paginated replay run list."""
    total: int
    limit: int
    offset: int
    runs: List[ReplayRunResponse]


class ReplayResultItem(BaseModel):
    """Single replay result."""
    id: str
    run_id: str
    interaction_id: Optional[str] = None
    original_prompt: Optional[str] = None
    original_response: Optional[str] = None
    replayed_response: Optional[str] = None
    similarity_score: float
    verdict: Optional[str] = None
    diff_summary: Optional[str] = None
    created_at: Optional[str] = None


class ReplayResultsResponse(BaseModel):
    """Paginated replay results."""
    total: int
    limit: int
    offset: int
    results: List[ReplayResultItem]
