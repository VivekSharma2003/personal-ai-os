"""
Personal AI OS - Profile Routes

REST endpoints for prompt profile management.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.dependencies import get_db
from app.services.profile_service import ProfileService
from app.api.schemas.profiles import CreateProfileRequest, UpdateProfileRequest, CloneProfileRequest

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.post("/profiles")
async def create_profile(
    body: CreateProfileRequest,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new prompt profile."""
    service = ProfileService(db)
    profile = await service.create_profile(
        user_id=user_id,
        name=body.name,
        description=body.description,
        rule_filter_tags=body.rule_filter_tags,
        rule_filter_categories=body.rule_filter_categories,
        system_preamble=body.system_preamble,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        is_default=body.is_default,
    )
    await db.commit()
    return profile.to_dict()


@router.get("/profiles")
async def list_profiles(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all prompt profiles for the user."""
    service = ProfileService(db)
    profiles = await service.list_profiles(user_id)
    return {"profiles": profiles, "total": len(profiles)}


@router.get("/profiles/{profile_id}")
async def get_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a prompt profile by ID."""
    service = ProfileService(db)
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.to_dict()


@router.patch("/profiles/{profile_id}")
async def update_profile(
    profile_id: UUID,
    body: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a prompt profile."""
    service = ProfileService(db)
    try:
        updates = body.model_dump(exclude_none=True)
        profile = await service.update_profile(profile_id, **updates)
        await db.commit()
        return profile.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/profiles/{profile_id}")
async def delete_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a prompt profile."""
    service = ProfileService(db)
    deleted = await service.delete_profile(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.commit()
    return {"status": "deleted"}


@router.post("/profiles/{profile_id}/clone")
async def clone_profile(
    profile_id: UUID,
    body: CloneProfileRequest,
    db: AsyncSession = Depends(get_db),
):
    """Clone a prompt profile with a new name."""
    service = ProfileService(db)
    try:
        clone = await service.clone_profile(profile_id, body.new_name)
        await db.commit()
        return clone.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
