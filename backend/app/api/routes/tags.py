"""
Personal AI OS - Tag API Routes
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.tags import (
    TagCreateRequest, TagUpdateRequest,
    TagResponse, TagListResponse,
    TagRuleRequest, BulkTagRequest, BulkTagResponse,
    RuleWithTagsResponse,
)
from app.dependencies import get_db
from app.services.tag_service import TagService
from app.services.rule_engine import RuleEngineService


router = APIRouter()


# --- Tag CRUD ---

@router.post("/tags", response_model=TagResponse)
async def create_tag(
    request: TagCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new tag."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(request.user_id)

    tag_service = TagService(db)
    tag = await tag_service.create_tag(
        user_id=user.id,
        name=request.name,
        color=request.color,
    )

    await db.commit()
    return TagResponse(**tag.to_dict())


@router.get("/tags", response_model=TagListResponse)
async def list_tags(
    user_id: str = Query(..., description="External user ID"),
    db: AsyncSession = Depends(get_db),
):
    """List all tags for a user (with rule counts)."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    tag_service = TagService(db)
    tags = await tag_service.list_tags(user.id)

    return TagListResponse(
        tags=[TagResponse(**t.to_dict(include_rule_count=True)) for t in tags],
        total=len(tags),
    )


@router.patch("/tags/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: str,
    request: TagUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a tag's name or color."""
    tag_service = TagService(db)
    tag = await tag_service.update_tag(
        tag_id=UUID(tag_id),
        name=request.name,
        color=request.color,
    )

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    await db.commit()
    return TagResponse(**tag.to_dict())


@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a tag (removes all rule associations)."""
    tag_service = TagService(db)
    deleted = await tag_service.delete_tag(UUID(tag_id))

    if not deleted:
        raise HTTPException(status_code=404, detail="Tag not found")

    await db.commit()
    return {"status": "deleted", "tag_id": tag_id}


# --- Rule-Tag Associations ---

@router.post("/rules/{rule_id}/tags")
async def tag_rule(
    rule_id: str,
    request: TagRuleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Attach tags to a rule."""
    tag_service = TagService(db)
    attached = await tag_service.tag_rule(
        rule_id=UUID(rule_id),
        tag_ids=[UUID(tid) for tid in request.tag_ids],
    )

    await db.commit()
    return {
        "rule_id": rule_id,
        "tags_attached": attached,
        "count": len(attached),
    }


@router.delete("/rules/{rule_id}/tags")
async def untag_rule(
    rule_id: str,
    request: TagRuleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Remove tags from a rule."""
    tag_service = TagService(db)
    removed = await tag_service.untag_rule(
        rule_id=UUID(rule_id),
        tag_ids=[UUID(tid) for tid in request.tag_ids],
    )

    await db.commit()
    return {
        "rule_id": rule_id,
        "tags_removed": removed,
        "count": len(removed),
    }


@router.get("/tags/{tag_id}/rules", response_model=list[RuleWithTagsResponse])
async def get_rules_by_tag(
    tag_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all rules that have a specific tag."""
    tag_service = TagService(db)
    rules = await tag_service.get_rules_by_tag(UUID(tag_id))

    return [
        RuleWithTagsResponse(
            id=str(r.id),
            content=r.content,
            category=r.category,
            confidence=round(r.confidence, 2),
            status=r.status,
        )
        for r in rules
    ]


@router.post("/tags/bulk", response_model=BulkTagResponse)
async def bulk_tag_rules(
    request: BulkTagRequest,
    db: AsyncSession = Depends(get_db),
):
    """Bulk-attach tags to multiple rules."""
    tag_service = TagService(db)
    result = await tag_service.bulk_tag(
        rule_ids=[UUID(rid) for rid in request.rule_ids],
        tag_ids=[UUID(tid) for tid in request.tag_ids],
    )

    await db.commit()
    return BulkTagResponse(**result)
