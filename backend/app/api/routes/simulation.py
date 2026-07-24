"""
Personal AI OS - Simulation Routes

REST endpoints for rule impact simulation (dry-run "what-if" analysis).
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.dependencies import get_db
from app.services.simulation_service import SimulationService
from app.api.schemas.simulation import SimulateRuleRequest, SimulateEditRequest

router = APIRouter()


def _get_user_id(x_user_id: str = Header(...)) -> UUID:
    return UUID(x_user_id)


@router.post("/simulate/rule")
async def simulate_rule(
    body: SimulateRuleRequest,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate adding a new rule.

    Generates responses with and without the draft rule for each test prompt
    to preview impact before committing.
    """
    service = SimulationService(db)
    return await service.simulate_rule(
        user_id=user_id,
        draft_rule_content=body.draft_rule_content,
        test_prompts=body.test_prompts,
    )


@router.post("/simulate/edit")
async def simulate_edit(
    body: SimulateEditRequest,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate editing an existing rule.

    Compares responses using old vs. new rule content for each test prompt.
    """
    service = SimulationService(db)
    result = await service.simulate_edit(
        user_id=user_id,
        rule_id=UUID(body.rule_id),
        new_content=body.new_content,
        test_prompts=body.test_prompts,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
