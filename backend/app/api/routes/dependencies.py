"""
Personal AI OS - Rule Dependencies API Routes
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.dependencies import (
    DependencyCreateRequest,
    DependencyResponse,
    DependencyListResponse,
    DependencyGraphResponse,
)
from app.dependencies import get_db
from app.services.rule_engine import RuleEngineService
from app.services.dependency_service import DependencyService


router = APIRouter()


@router.post(
    "/rules/{rule_id}/dependencies",
    response_model=DependencyResponse,
    status_code=201,
    summary="Add a dependency to a rule",
)
async def add_dependency(
    rule_id: UUID,
    request: DependencyCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a dependency between two rules.

    Dependency types:
      - **requires**: child only active when parent is active
      - **excludes**: child only active when parent is NOT active
      - **enhances**: advisory only (no enforcement)

    Cycle detection prevents circular dependencies.
    """
    service = DependencyService(db)

    try:
        dep = await service.add_dependency(
            rule_id=rule_id,
            depends_on_rule_id=UUID(request.depends_on_rule_id),
            dependency_type=request.dependency_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not dep:
        raise HTTPException(status_code=400, detail="Could not create dependency")

    return DependencyResponse(**dep.to_dict())


@router.get(
    "/rules/{rule_id}/dependencies",
    response_model=DependencyListResponse,
    summary="List dependencies for a rule",
)
async def list_dependencies(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all rules that this rule depends on."""
    service = DependencyService(db)
    deps = await service.get_dependencies(rule_id)

    return DependencyListResponse(
        dependencies=[DependencyResponse(**d) for d in deps],
        total=len(deps),
    )


@router.get(
    "/rules/{rule_id}/dependents",
    response_model=DependencyListResponse,
    summary="List rules that depend on this rule",
)
async def list_dependents(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all rules that depend on this rule."""
    service = DependencyService(db)
    deps = await service.get_dependents(rule_id)

    return DependencyListResponse(
        dependencies=[DependencyResponse(**d) for d in deps],
        total=len(deps),
    )


@router.delete(
    "/dependencies/{dep_id}",
    summary="Remove a dependency",
)
async def remove_dependency(
    dep_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove a dependency link between two rules."""
    service = DependencyService(db)
    removed = await service.remove_dependency(dep_id)

    if not removed:
        raise HTTPException(status_code=404, detail="Dependency not found")

    return {"status": "deleted", "id": str(dep_id)}


@router.get(
    "/rules/dependency-graph",
    response_model=DependencyGraphResponse,
    summary="Get full dependency graph",
)
async def get_dependency_graph(
    user_id: str = Query(..., description="External user ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the full dependency graph for a user's rules.

    Returns nodes (rules) and edges (dependencies) suitable
    for visualization.
    """
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    service = DependencyService(db)
    graph = await service.get_dependency_graph(user.id)
    return graph
