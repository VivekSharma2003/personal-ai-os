"""
Personal AI OS - Job Dashboard Schemas
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class JobRunResponse(BaseModel):
    """Record of a single job execution."""
    job_id: str
    started_at: str
    finished_at: str
    status: str = Field(description="'success' or 'failure'")
    duration_ms: float
    detail: Optional[str] = None


class JobStatsResponse(BaseModel):
    """Aggregate stats for a single job."""
    total_runs: int
    success_count: int
    failure_count: int
    avg_duration_ms: float
    success_rate: float = Field(description="Percentage 0-100")
    last_run_at: Optional[str] = None
    last_status: Optional[str] = None


class JobInfoResponse(BaseModel):
    """Information about a registered background job."""
    id: str
    name: str
    trigger: str
    next_run_time: Optional[str] = None
    is_paused: bool = False
    stats: JobStatsResponse


class JobListResponse(BaseModel):
    """List of all registered background jobs."""
    jobs: List[JobInfoResponse]
    total: int


class JobHistoryResponse(BaseModel):
    """Run history for a specific job."""
    job_id: str
    runs: List[JobRunResponse]
    stats: JobStatsResponse
