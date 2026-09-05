"""
Personal AI OS - MoE Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.dependencies import get_db
from app.services.moe_router import MoERouterService

router = APIRouter(prefix="/api/moe", tags=["MoE"])

class RouteConfig(BaseModel):
    intent: str
    provider: str
    model: str
    
class RouteRequest(BaseModel):
    prompt: str

@router.post("/route")
async def get_route(
    request: RouteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Determine the optimal provider/model for a given prompt."""
    service = MoERouterService(db)
    route = await service.get_route_for_prompt(request.prompt)
    return route

@router.post("/configure")
async def configure_route(
    config: RouteConfig,
    db: AsyncSession = Depends(get_db)
):
    """Configure the routing mapping for a specific intent."""
    service = MoERouterService(db)
    route = await service.configure_route(config.intent, config.provider, config.model)
    return {
        "intent": route.intent,
        "provider": route.provider,
        "model": route.model
    }
