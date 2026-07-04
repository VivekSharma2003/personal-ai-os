"""
Personal AI OS - Session Routes

REST endpoints for session security and IP allowlisting.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.dependencies import get_db
from app.services.session_service import SessionService
from app.api.schemas.sessions import IPAllowlistRequest

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.get("/sessions")
async def list_sessions(
    since_hours: int = Query(default=24, ge=1, le=720),
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List active sessions for the user."""
    service = SessionService(db)
    sessions = await service.get_active_sessions(user_id, since_hours)
    return {"sessions": sessions, "total": len(sessions)}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Revoke (delete) a specific session."""
    service = SessionService(db)
    deleted = await service.revoke_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.commit()
    return {"status": "revoked"}


@router.put("/keys/{key_id}/ip-allowlist")
async def set_ip_allowlist(
    key_id: UUID,
    body: IPAllowlistRequest,
    db: AsyncSession = Depends(get_db),
):
    """Set IP allowlist for an API key."""
    service = SessionService(db)
    try:
        result = await service.set_ip_allowlist(key_id, body.cidrs)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/keys/{key_id}/ip-allowlist")
async def get_ip_allowlist(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get IP allowlist for an API key."""
    service = SessionService(db)
    try:
        allowlist = await service.get_ip_allowlist(key_id)
        return {"api_key_id": str(key_id), "ip_allowlist": allowlist}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sessions/anomalies")
async def detect_anomalies(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Detect anomalous session patterns."""
    service = SessionService(db)
    anomalies = await service.detect_anomalies(user_id)
    return {"anomalies": anomalies, "total": len(anomalies)}
