"""
Personal AI OS - API Key Management Routes
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.api_keys import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
)
from app.dependencies import get_db
from app.services.rule_engine import RuleEngineService
from app.services.api_key_service import APIKeyService


router = APIRouter()


@router.post(
    "/keys",
    response_model=APIKeyCreateResponse,
    status_code=201,
    summary="Create a new API key",
)
async def create_api_key(
    request: APIKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API key for authenticated access.

    The raw key is returned **only once** in the response. Store it securely —
    it cannot be retrieved again.
    """
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(request.user_id)

    service = APIKeyService(db)
    api_key, raw_key = await service.create_key(
        user_id=user.id,
        name=request.name,
        scopes=request.scopes,
        expires_in_days=request.expires_in_days,
    )

    return APIKeyCreateResponse(
        id=str(api_key.id),
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        raw_key=raw_key,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        created_at=api_key.created_at.isoformat() if api_key.created_at else None,
    )


@router.get(
    "/keys",
    response_model=APIKeyListResponse,
    summary="List API keys for a user",
)
async def list_api_keys(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for a user (metadata only, never the raw key)."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    service = APIKeyService(db)
    keys = await service.list_keys(user.id)

    return APIKeyListResponse(
        keys=[APIKeyResponse(**k.to_dict()) for k in keys],
        total=len(keys),
    )


@router.delete(
    "/keys/{key_id}",
    response_model=APIKeyResponse,
    summary="Revoke an API key",
)
async def revoke_api_key(
    key_id: UUID,
    user_id: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key. The key will immediately stop working."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    service = APIKeyService(db)
    revoked = await service.revoke_key(key_id, user.id)

    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")

    return APIKeyResponse(**revoked.to_dict())


@router.post(
    "/keys/{key_id}/rotate",
    response_model=APIKeyCreateResponse,
    summary="Rotate an API key",
)
async def rotate_api_key(
    key_id: UUID,
    user_id: str = "",
    db: AsyncSession = Depends(get_db),
):
    """
    Rotate an API key: revoke the old one and create a new one
    with the same name and scopes.
    """
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    service = APIKeyService(db)
    result = await service.rotate_key(key_id, user.id)

    if not result:
        raise HTTPException(status_code=404, detail="API key not found")

    new_key, raw_key = result

    return APIKeyCreateResponse(
        id=str(new_key.id),
        name=new_key.name,
        key_prefix=new_key.key_prefix,
        raw_key=raw_key,
        scopes=new_key.scopes,
        expires_at=new_key.expires_at.isoformat() if new_key.expires_at else None,
        created_at=new_key.created_at.isoformat() if new_key.created_at else None,
    )
