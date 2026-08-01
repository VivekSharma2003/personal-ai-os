"""
Personal AI OS - Rule Graph Routes

REST API endpoints to analyze rule dependency DAGs, topological ordering, cycle detection,
and conflict-prone paths.
"""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.dependencies import get_db
from app.services.rule_graph_service import RuleGraphService
from app.api.schemas.rule_graph import RuleGraphTopologyResponse, CycleDetectionResponse, ConflictPathResponse

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.get("/rules/graph/topology", response_model=RuleGraphTopologyResponse)
async def get_topology(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the dependency graph mapping and a valid topological execution order of rules."""
    service = RuleGraphService(db)
    return await service.get_topology(user_id)


@router.get("/rules/graph/cycles", response_model=CycleDetectionResponse)
async def detect_cycles(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Scan active rules and detect dependency cycle paths that would cause resolution failures."""
    service = RuleGraphService(db)
    return await service.detect_cycles(user_id)


@router.get("/rules/graph/conflict-paths", response_model=List[ConflictPathResponse])
async def analyze_conflict_paths(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Identify rules with transitive dependency chains that lead to logical exclusion conflicts."""
    service = RuleGraphService(db)
    return await service.analyze_conflict_paths(user_id)
