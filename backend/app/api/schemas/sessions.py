"""
Personal AI OS - Session Schemas

Pydantic schemas for session security and IP allowlisting.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class SessionResponse(BaseModel):
    """Active session details."""
    id: str
    user_id: str
    api_key_id: Optional[str] = None
    ip_address: str
    user_agent: str
    request_count: int
    last_seen_at: Optional[str] = None
    created_at: Optional[str] = None


class SessionListResponse(BaseModel):
    """List of active sessions."""
    sessions: List[SessionResponse]
    total: int


class IPAllowlistRequest(BaseModel):
    """Request to set IP allowlist."""
    cidrs: List[str] = Field(..., min_length=0, max_length=50)


class IPAllowlistResponse(BaseModel):
    """IP allowlist for an API key."""
    api_key_id: str
    ip_allowlist: List[str]


class AnomalyResponse(BaseModel):
    """Detected anomalous session."""
    type: str
    severity: str
    detail: str
    session_id: Optional[str] = None
    api_key_id: Optional[str] = None
    ip_address: Optional[str] = None
    request_count: Optional[int] = None
    unique_ips: Optional[int] = None


class AnomalyListResponse(BaseModel):
    """List of detected anomalies."""
    anomalies: List[AnomalyResponse]
    total: int
