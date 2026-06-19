"""
Personal AI OS - Data Retention Policy API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.retention import (
    RetentionPoliciesResponse,
    RetentionPolicyResponse,
    RetentionPolicySetRequest,
    CleanupPreviewResponse,
    CleanupResultResponse,
    StorageStatsResponse,
    StorageStatsResource,
)
from app.dependencies import get_db
from app.services.rule_engine import RuleEngineService
from app.services.retention_service import RetentionService


router = APIRouter()


@router.get(
    "/retention",
    response_model=RetentionPoliciesResponse,
    summary="Get retention policies",
)
async def get_retention_policies(
    user_id: str = Query(..., description="External user ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all retention policies for a user.

    Includes system defaults for any resource types without custom policies.
    """
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    service = RetentionService(db)
    policies = await service.get_policies(user.id)

    return RetentionPoliciesResponse(
        policies=[RetentionPolicyResponse(**p) for p in policies]
    )


@router.put(
    "/retention",
    response_model=RetentionPolicyResponse,
    summary="Set a retention policy",
)
async def set_retention_policy(
    request: RetentionPolicySetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create or update a retention policy for a resource type.

    Set `retention_days` to 0 to keep records forever.
    """
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(request.user_id)

    service = RetentionService(db)

    try:
        policy = await service.set_policy(
            user.id, request.resource_type, request.retention_days
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RetentionPolicyResponse(
        **policy.to_dict(),
        is_custom=True,
    )


@router.post(
    "/retention/preview",
    response_model=CleanupPreviewResponse,
    summary="Preview cleanup (dry run)",
)
async def preview_cleanup(
    user_id: str = Query(..., description="External user ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Dry-run preview showing how many records would be deleted
    for each resource type based on current retention policies.
    """
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    service = RetentionService(db)
    preview = await service.preview_cleanup(user.id)

    return CleanupPreviewResponse(would_delete=preview)


@router.post(
    "/retention/cleanup",
    response_model=CleanupResultResponse,
    summary="Run cleanup now",
)
async def run_cleanup(
    user_id: str = Query(..., description="External user ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger a retention cleanup for the user.

    Deletes records older than the configured retention periods.
    """
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    service = RetentionService(db)
    deleted = await service.execute_cleanup(user.id)

    return CleanupResultResponse(deleted=deleted)


@router.get(
    "/retention/stats",
    response_model=StorageStatsResponse,
    summary="Get storage usage stats",
)
async def get_storage_stats(
    user_id: str = Query(..., description="External user ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get record counts and date ranges per resource type.
    """
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    service = RetentionService(db)
    stats = await service.get_storage_stats(user.id)

    return StorageStatsResponse(
        stats={k: StorageStatsResource(**v) for k, v in stats.items()}
    )
