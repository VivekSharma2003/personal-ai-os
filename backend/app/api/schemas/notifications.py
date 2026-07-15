"""
Personal AI OS - Notification Schemas

Pydantic schemas for notifications and digests.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class NotificationResponse(BaseModel):
    """Single notification."""
    id: str
    user_id: str
    type: str
    title: str
    body: Optional[str] = None
    extra_data: Dict = {}
    is_read: bool
    is_archived: bool
    created_at: Optional[str] = None
    read_at: Optional[str] = None


class NotificationListResponse(BaseModel):
    """Paginated notification list."""
    total: int
    limit: int
    offset: int
    notifications: List[NotificationResponse]


class UnreadCountResponse(BaseModel):
    """Unread notification count with type breakdown."""
    unread_count: int
    by_type: Dict[str, int] = {}


class DigestResponse(BaseModel):
    """Generated activity digest."""
    digest: str
    event_count: int
    event_breakdown: Dict[str, int] = {}
    period: str
