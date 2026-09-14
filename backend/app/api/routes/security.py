"""
Personal AI OS - Security Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.services.injection_defense import InjectionDefenseService

router = APIRouter(prefix="/api/security", tags=["Security"])

class PromptEvaluationRequest(BaseModel):
    prompt: str

class PromptEvaluationResponse(BaseModel):
    is_safe: bool
    reason: str = ""

@router.post("/evaluate-prompt", response_model=PromptEvaluationResponse)
async def evaluate_prompt(request: PromptEvaluationRequest):
    """
    Evaluates a prompt for potential injection or jailbreak attempts.
    """
    service = InjectionDefenseService()
    is_safe, reason = service.evaluate_prompt(request.prompt)
    
    return PromptEvaluationResponse(is_safe=is_safe, reason=reason)
