"""
Personal AI OS - Notification Routes

REST endpoints for notification management and digest generation.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.dependencies import get_db
from app.services.notification_service import NotificationService

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.get("/notifications")
async def list_notifications(
    unread_only: bool = Query(default=False),
    type_filter: str = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the user."""
    service = NotificationService(db)
    return await service.list_notifications(user_id, unread_only, type_filter, limit, offset)


@router.get("/notifications/unread-count")
async def get_unread_count(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get unread notification count for badge display."""
    service = NotificationService(db)
    return await service.get_unread_count(user_id)


@router.patch("/notifications/{notification_id}/read")
async def mark_read(
    notification_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    service = NotificationService(db)
    result = await service.mark_read(notification_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.patch("/notifications/read-all")
async def mark_all_read(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read."""
    service = NotificationService(db)
    return await service.mark_all_read(user_id)


@router.get("/notifications/digest")
async def generate_digest(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate an LLM-powered daily digest of rule activity."""
    service = NotificationService(db)
    return await service.generate_digest(user_id)


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete (archive) a notification."""
    service = NotificationService(db)
    result = await service.delete_notification(notification_id, user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
