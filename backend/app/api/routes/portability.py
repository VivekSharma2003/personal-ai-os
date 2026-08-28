"""
Personal AI OS - Portability Routes
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.user import User
from app.services.rule_engine import RuleEngineService
from app.services.portability_service import PortabilityService
from app.api.schemas.portability import (
    ExportRequest,
    ExportResponse,
    ImportRequest,
    ImportResponse
)

router = APIRouter(prefix="/api/portability", tags=["Portability"])


async def get_current_user_from_header(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
) -> User:
    service = RuleEngineService(db)
    return await service.get_or_create_user(x_user_id)


@router.post("/export", response_model=ExportResponse)
async def export_rules(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header)
):
    """Export user rules as a payload (optionally encrypted)."""
    service = PortabilityService(db)
    payload = await service.export_rules(current_user.id, request.encrypt)
    return ExportResponse(payload=payload, is_encrypted=request.encrypt)


@router.post("/import", response_model=ImportResponse)
async def import_rules(
    request: ImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_from_header)
):
    """Import user rules from a payload."""
    service = PortabilityService(db)
    result = await service.import_rules(current_user.id, request.payload, request.is_encrypted)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
        
    return ImportResponse(**result)
