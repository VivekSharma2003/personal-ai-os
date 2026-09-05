"""
Personal AI OS - Mixture of Experts (MoE) Request Router
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.expert_route import ExpertRoute

logger = logging.getLogger(__name__)

class MoERouterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _classify_intent(self, prompt: str) -> str:
        """
        Classifies the intent of a prompt. 
        In production, this could be a fast LLM call or a local embedding/classifier model.
        For MVP, we use heuristic keyword matching.
        """
        prompt_lower = prompt.lower()
        if any(kw in prompt_lower for kw in ["code", "python", "bug", "refactor", "function", "api"]):
            return "coding"
        if any(kw in prompt_lower for kw in ["summarize", "tl;dr", "summary", "brief"]):
            return "summarization"
        if any(kw in prompt_lower for kw in ["translate", "spanish", "french", "language"]):
            return "translation"
        
        return "general"

    async def get_route_for_prompt(self, prompt: str) -> Dict[str, str]:
        """
        Returns the optimal provider and model for the given prompt.
        """
        intent = await self._classify_intent(prompt)
        
        result = await self.db.execute(
            select(ExpertRoute).where(ExpertRoute.intent == intent)
        )
        route = result.scalars().first()
        
        if route:
            return {
                "intent": intent,
                "provider": route.provider,
                "model": route.model
            }
            
        # Default fallback
        return {
            "intent": intent,
            "provider": "openai",
            "model": "gpt-4o"
        }
        
    async def configure_route(self, intent: str, provider: str, model: str) -> ExpertRoute:
        """Configure or update an expert route."""
        result = await self.db.execute(
            select(ExpertRoute).where(ExpertRoute.intent == intent)
        )
        route = result.scalars().first()
        
        if route:
            route.provider = provider
            route.model = model
        else:
            route = ExpertRoute(intent=intent, provider=provider, model=model)
            self.db.add(route)
            
        await self.db.commit()
        await self.db.refresh(route)
        return route
