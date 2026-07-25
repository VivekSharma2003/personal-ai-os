"""
Personal AI OS - Rule Model Config Routes

REST API routes for managing rule-specific LLM settings and formatting optimizations.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.dependencies import get_db
from app.services.rule_model_config_service import RuleModelConfigService
from app.api.schemas.rule_model_configs import RuleModelConfigUpsert, RuleModelConfigResponse

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.post("/rules/{rule_id}/model-configs", response_model=dict)
async def create_or_update_model_config(
    rule_id: UUID,
    body: RuleModelConfigUpsert,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Add or update model-specific configuration overrides for a rule."""
    service = RuleModelConfigService(db)
    result = await service.create_or_update_override(
        user_id=user_id,
        rule_id=rule_id,
        provider=body.provider,
        model_name=body.model_name,
        temperature_override=body.temperature_override,
        max_tokens_override=body.max_tokens_override,
        optimized_content=body.optimized_content,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/rules/{rule_id}/model-configs", response_model=List[RuleModelConfigResponse])
async def list_model_configs(
    rule_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all model overrides/configurations associated with a specific rule."""
    service = RuleModelConfigService(db)
    return await service.list_overrides(rule_id, user_id)


@router.delete("/rules/model-configs/{config_id}", response_model=dict)
async def delete_model_config(
    config_id: UUID,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific rule model configuration override."""
    service = RuleModelConfigService(db)
    result = await service.delete_override(config_id, user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
