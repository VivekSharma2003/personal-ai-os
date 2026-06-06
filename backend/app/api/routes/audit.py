"""
Personal AI OS - Audit Trail API Routes
"""
import math
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
# pyrefly: ignore [missing-import]
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.audit import AuditLogResponse, AuditListResponse, AuditStatsResponse
from app.dependencies import get_db
from app.services.audit_service import AuditService
from app.services.rule_engine import RuleEngineService


router = APIRouter()


@router.get("/audit", response_model=AuditListResponse)
async def list_audit_logs(
    user_id: str = Query(..., description="External user ID"),
    event_type: str = Query(None, description="Filter by event type"),
    rule_id: str = Query(None, description="Filter by rule ID"),
    from_date: str = Query(None, description="Start date (ISO 8601)"),
    to_date: str = Query(None, description="End date (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated audit logs with optional filters."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    # Parse dates
    parsed_from = datetime.fromisoformat(from_date) if from_date else None
    parsed_to = datetime.fromisoformat(to_date) if to_date else None
    parsed_rule_id = UUID(rule_id) if rule_id else None

    audit_service = AuditService(db)
    logs, total = await audit_service.list_logs(
        user_id=user.id,
        event_type=event_type,
        rule_id=parsed_rule_id,
        from_date=parsed_from,
        to_date=parsed_to,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return AuditListResponse(
        logs=[AuditLogResponse(**log.to_dict()) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/audit/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    user_id: str = Query(..., description="External user ID"),
    from_date: str = Query(None, description="Start date (ISO 8601)"),
    to_date: str = Query(None, description="End date (ISO 8601)"),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated audit log statistics."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    parsed_from = datetime.fromisoformat(from_date) if from_date else None
    parsed_to = datetime.fromisoformat(to_date) if to_date else None

    audit_service = AuditService(db)
    stats = await audit_service.get_stats(
        user_id=user.id,
        from_date=parsed_from,
        to_date=parsed_to,
    )

    most_recent = None
    if stats["most_recent"]:
        most_recent = AuditLogResponse(**stats["most_recent"])

    return AuditStatsResponse(
        total_events=stats["total_events"],
        event_counts=stats["event_counts"],
        most_recent=most_recent,
    )


@router.get("/audit/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single audit log entry by ID."""
    audit_service = AuditService(db)
    log = await audit_service.get_log(UUID(log_id))

    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return AuditLogResponse(**log.to_dict())


@router.get("/audit/export/csv")
async def export_audit_csv(
    user_id: str = Query(..., description="External user ID"),
    event_type: str = Query(None, description="Filter by event type"),
    from_date: str = Query(None, description="Start date (ISO 8601)"),
    to_date: str = Query(None, description="End date (ISO 8601)"),
    db: AsyncSession = Depends(get_db),
):
    """Export audit logs as a downloadable CSV file."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    parsed_from = datetime.fromisoformat(from_date) if from_date else None
    parsed_to = datetime.fromisoformat(to_date) if to_date else None

    audit_service = AuditService(db)
    csv_content = await audit_service.export_csv(
        user_id=user.id,
        event_type=event_type,
        from_date=parsed_from,
        to_date=parsed_to,
    )

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
