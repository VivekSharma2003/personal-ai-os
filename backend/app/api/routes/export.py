"""
Personal AI OS - Export & Backup API Routes
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.export import (
    ExportResponse, ExportMetadata, ExportedRule,
    ExportedInteraction, ExportedAuditEvent
)
from app.dependencies import get_db
from app.services.rule_engine import RuleEngineService
from app.models.rule import Rule
from app.models.interaction import Interaction
from app.models.audit_log import AuditLog


router = APIRouter()


@router.get("/export", response_model=ExportResponse)
async def export_data(
    user_id: str = Query(..., description="External user ID"),
    include: Optional[str] = Query(
        None,
        description="Comma-separated list of what to include: rules,interactions,audit. Default: all."
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Export all user data as JSON for backup/portability.

    Supports filtered exports via the 'include' parameter:
    - 'rules' — export only rules
    - 'interactions' — export only conversations
    - 'audit' — export only audit events
    - Default (None) — export everything
    """
    rule_engine = RuleEngineService(db)

    try:
        user = await rule_engine.get_or_create_user(user_id)

        # Determine what to include
        include_set = set()
        if include:
            include_set = {s.strip().lower() for s in include.split(",")}
        include_all = len(include_set) == 0

        # --- Rules ---
        rules_list = []
        if include_all or "rules" in include_set:
            result = await db.execute(
                select(Rule)
                .where(Rule.user_id == user.id)
                .order_by(Rule.created_at.desc())
            )
            rules = result.scalars().all()
            rules_list = [
                ExportedRule(
                    id=str(r.id),
                    content=r.content,
                    original_correction=r.original_correction,
                    category=r.category,
                    confidence=round(r.confidence, 2),
                    times_applied=r.times_applied,
                    times_reinforced=r.times_reinforced,
                    status=r.status,
                    created_at=r.created_at.isoformat() if r.created_at else None,
                    updated_at=r.updated_at.isoformat() if r.updated_at else None,
                    last_applied_at=r.last_applied_at.isoformat() if r.last_applied_at else None,
                )
                for r in rules
            ]

        # --- Interactions ---
        interactions_list = []
        if include_all or "interactions" in include_set:
            result = await db.execute(
                select(Interaction)
                .where(Interaction.user_id == user.id)
                .order_by(Interaction.created_at.desc())
            )
            interactions = result.scalars().all()
            interactions_list = [
                ExportedInteraction(
                    id=str(i.id),
                    conversation_id=i.conversation_id,
                    user_message=i.user_message,
                    assistant_response=i.assistant_response,
                    rules_applied=[str(r) for r in (i.rules_applied or [])],
                    was_corrected=i.was_corrected or False,
                    correction_text=i.correction_text,
                    created_at=i.created_at.isoformat() if i.created_at else None,
                )
                for i in interactions
            ]

        # --- Audit Events ---
        audit_list = []
        if include_all or "audit" in include_set:
            result = await db.execute(
                select(AuditLog)
                .where(AuditLog.user_id == user.id)
                .order_by(AuditLog.created_at.desc())
            )
            events = result.scalars().all()
            audit_list = [
                ExportedAuditEvent(
                    id=str(e.id),
                    rule_id=str(e.rule_id) if e.rule_id else None,
                    event_type=e.event_type,
                    event_data=e.event_data or {},
                    created_at=e.created_at.isoformat() if e.created_at else None,
                )
                for e in events
            ]

        # Build metadata
        metadata = ExportMetadata(
            exported_at=datetime.utcnow().isoformat(),
            version="1.0.0",
            user_id=user_id,
            total_rules=len(rules_list),
            total_interactions=len(interactions_list),
            total_audit_events=len(audit_list),
        )

        return ExportResponse(
            metadata=metadata,
            rules=rules_list,
            interactions=interactions_list,
            audit_events=audit_list,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
