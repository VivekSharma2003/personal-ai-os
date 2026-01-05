"""
Personal AI OS - Rules API Routes
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.rules import (
    RuleCreate, RuleUpdate, RuleResponse, RulesListResponse,
    AuditEventResponse, AuditLogResponse
)
from app.dependencies import get_db
from app.services.rule_engine import RuleEngineService
from app.models.rule import Rule, RuleStatus
from app.models.audit_log import AuditLog


router = APIRouter()


@router.get("/rules", response_model=RulesListResponse)
async def list_rules(
    user_id: str = Query(..., description="External user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all rules for a user with optional filters.
    """
    service = RuleEngineService(db)
    
    try:
        # Get or create user
        user = await service.get_or_create_user(user_id)
        
        # Get rules with filters
        rules = await service.get_user_rules(
            user_id=user.id,
            status=status,
            category=category
        )
        
        # Count by status
        all_rules = await service.get_user_rules(user_id=user.id)
        active_count = sum(1 for r in all_rules if r.status == RuleStatus.ACTIVE.value)
        archived_count = sum(1 for r in all_rules if r.status == RuleStatus.ARCHIVED.value)
        disabled_count = sum(1 for r in all_rules if r.status == RuleStatus.DISABLED.value)
        
        return RulesListResponse(
            rules=[RuleResponse(
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
                last_applied_at=r.last_applied_at.isoformat() if r.last_applied_at else None
            ) for r in rules],
            total=len(all_rules),
            active=active_count,
            archived=archived_count,
            disabled=disabled_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific rule by ID.
    """
    service = RuleEngineService(db)
    
    try:
        rule = await service.get_rule(UUID(rule_id))
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return RuleResponse(
            id=str(rule.id),
            content=rule.content,
            original_correction=rule.original_correction,
            category=rule.category,
            confidence=round(rule.confidence, 2),
            times_applied=rule.times_applied,
            times_reinforced=rule.times_reinforced,
            status=rule.status,
            created_at=rule.created_at.isoformat() if rule.created_at else None,
            updated_at=rule.updated_at.isoformat() if rule.updated_at else None,
            last_applied_at=rule.last_applied_at.isoformat() if rule.last_applied_at else None
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    update: RuleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a rule's content, category, or status.
    """
    service = RuleEngineService(db)
    
    try:
        rule = await service.update_rule(
            rule_id=UUID(rule_id),
            content=update.content,
            status=update.status,
            category=update.category
        )
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        await db.commit()
        
        return RuleResponse(
            id=str(rule.id),
            content=rule.content,
            original_correction=rule.original_correction,
            category=rule.category,
            confidence=round(rule.confidence, 2),
            times_applied=rule.times_applied,
            times_reinforced=rule.times_reinforced,
            status=rule.status,
            created_at=rule.created_at.isoformat() if rule.created_at else None,
            updated_at=rule.updated_at.isoformat() if rule.updated_at else None,
            last_applied_at=rule.last_applied_at.isoformat() if rule.last_applied_at else None
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a rule permanently.
    """
    service = RuleEngineService(db)
    
    try:
        success = await service.delete_rule(UUID(rule_id))
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        await db.commit()
        
        return {"status": "deleted", "id": rule_id}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/{rule_id}/toggle", response_model=RuleResponse)
async def toggle_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Toggle a rule between active and disabled.
    """
    service = RuleEngineService(db)
    
    try:
        rule = await service.toggle_rule(UUID(rule_id))
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        await db.commit()
        
        return RuleResponse(
            id=str(rule.id),
            content=rule.content,
            original_correction=rule.original_correction,
            category=rule.category,
            confidence=round(rule.confidence, 2),
            times_applied=rule.times_applied,
            times_reinforced=rule.times_reinforced,
            status=rule.status,
            created_at=rule.created_at.isoformat() if rule.created_at else None,
            updated_at=rule.updated_at.isoformat() if rule.updated_at else None,
            last_applied_at=rule.last_applied_at.isoformat() if rule.last_applied_at else None
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit", response_model=AuditLogResponse)
async def get_audit_log(
    user_id: str = Query(..., description="External user ID"),
    rule_id: Optional[str] = Query(None, description="Filter by rule ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit log for a user with optional filters.
    """
    service = RuleEngineService(db)
    
    try:
        user = await service.get_or_create_user(user_id)
        
        query = select(AuditLog).where(AuditLog.user_id == user.id)
        
        if rule_id:
            query = query.where(AuditLog.rule_id == UUID(rule_id))
        if event_type:
            query = query.where(AuditLog.event_type == event_type)
        
        query = query.order_by(AuditLog.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        return AuditLogResponse(
            events=[AuditEventResponse(
                id=str(e.id),
                rule_id=str(e.rule_id) if e.rule_id else None,
                event_type=e.event_type,
                event_data=e.event_data or {},
                created_at=e.created_at.isoformat() if e.created_at else ""
            ) for e in events],
            total=len(events)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
