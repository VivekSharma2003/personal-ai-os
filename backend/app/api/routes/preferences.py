"""
Personal AI OS - User Preferences Routes

GET    /api/preferences          — fetch current preferences
PATCH  /api/preferences          — deep-merge one or more sections
DELETE /api/preferences/{section} — reset one section to {}
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.preferences_service import PreferencesService
from app.services.rule_engine import RuleEngineService

router = APIRouter(prefix="/api/preferences", tags=["User Preferences"])


async def _get_user(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db),
):
    return await RuleEngineService(db).get_or_create_user(x_user_id)


class PatchPreferencesRequest(BaseModel):
    llm: Optional[Dict[str, Any]] = None
    ui: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None
    custom: Optional[Dict[str, Any]] = None


@router.get("")
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_user),
):
    """Return the current user's full preferences."""
    service = PreferencesService(db)
    prefs = await service.get_or_create(current_user.id)
    return service._to_dict(prefs)


@router.patch("")
async def patch_preferences(
    req: PatchPreferencesRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_user),
):
    """Deep-merge the supplied sections into existing preferences."""
    service = PreferencesService(db)
    prefs = await service.patch(
        current_user.id,
        llm=req.llm,
        ui=req.ui,
        notifications=req.notifications,
        custom=req.custom,
    )
    return service._to_dict(prefs)


@router.delete("/{section}")
async def reset_section(
    section: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_get_user),
):
    """Reset a single preferences section back to an empty dict."""
    service = PreferencesService(db)
    try:
        prefs = await service.reset_section(current_user.id, section)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return service._to_dict(prefs)
