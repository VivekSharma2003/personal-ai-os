"""
Personal AI OS - Token Budget Routes

POST /api/token-budget/check    — validate a prompt against its model's context window
POST /api/token-budget/truncate — auto-trim a prompt to fit the budget
GET  /api/token-budget/limits   — list all known model limits
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.services.token_budget import TokenBudgetService, MODEL_LIMITS

router = APIRouter(prefix="/api/token-budget", tags=["Token Budget"])


class BudgetCheckRequest(BaseModel):
    provider: str
    model: str
    prompt: str
    reserved_output_tokens: int = Field(default=1024, ge=0, le=32768)


class TruncateRequest(BudgetCheckRequest):
    truncation_marker: Optional[str] = "\n\n[...truncated to fit context window...]"


@router.get("/limits")
async def list_limits():
    """Return the known context-window limits for every supported model."""
    return MODEL_LIMITS


@router.post("/check")
async def check_budget(req: BudgetCheckRequest):
    """
    Check whether a prompt fits inside the model's context window.
    Returns estimated token count, limit, and overflow.
    """
    service = TokenBudgetService()
    return service.check(req.provider, req.model, req.prompt, req.reserved_output_tokens)


@router.post("/truncate")
async def truncate_prompt(req: TruncateRequest):
    """
    Trim a prompt so it fits within the model's context window.
    Returns the (possibly shortened) prompt and the budget report.
    """
    service = TokenBudgetService()
    original_report = service.check(req.provider, req.model, req.prompt, req.reserved_output_tokens)
    truncated = service.truncate(
        req.provider, req.model, req.prompt,
        req.reserved_output_tokens, req.truncation_marker
    )
    final_report = service.check(req.provider, req.model, truncated, req.reserved_output_tokens)
    return {
        "original": original_report,
        "prompt": truncated,
        "final": final_report,
        "was_truncated": not original_report["within_budget"],
    }
