"""
Personal AI OS - LLM Fallback Service
"""
import asyncio
import logging
from typing import List, Dict, Optional, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.llm_fallback import LLMFallbackPolicy
from app.core.llm import OpenAIProvider, GeminiProvider, AnthropicProvider
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class FallbackService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get_policy(self, user_id: UUID, provider: str, model: str) -> Optional[LLMFallbackPolicy]:
        """Get an active fallback policy for a user and model/provider."""
        result = await self.db.execute(
            select(LLMFallbackPolicy)
            .where(
                LLMFallbackPolicy.user_id == user_id,
                LLMFallbackPolicy.primary_provider == provider,
                LLMFallbackPolicy.primary_model == model,
                LLMFallbackPolicy.is_active == True
            )
        )
        return result.scalars().first()
        
    def _get_provider_instance(self, provider_name: str, model_name: str):
        provider_name = provider_name.lower()
        if provider_name == "openai":
            provider = OpenAIProvider()
        elif provider_name == "gemini":
            provider = GeminiProvider()
        elif provider_name == "anthropic":
            provider = AnthropicProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
            
        provider.model = model_name
        return provider

    async def generate_response_with_fallback(
        self,
        user_id: UUID,
        messages: List[Dict[str, str]],
        primary_provider_name: str,
        primary_model_name: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Execute an LLM completion with automatic retries and fallback to a secondary model/provider.
        """
        policy = await self.get_policy(user_id, primary_provider_name, primary_model_name)
        
        if not policy:
            # No fallback policy, just use primary directly
            provider = self._get_provider_instance(primary_provider_name, primary_model_name)
            return await provider.generate_response(messages, temperature, max_tokens)
            
        # Execute with retry and fallback
        primary = self._get_provider_instance(policy.primary_provider, policy.primary_model)
        fallback = self._get_provider_instance(policy.fallback_provider, policy.fallback_model)
        
        last_exception = None
        
        # Primary attempts
        for attempt in range(policy.max_retries):
            try:
                return await primary.generate_response(messages, temperature, max_tokens)
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Primary LLM ({policy.primary_provider}/{policy.primary_model}) "
                    f"failed (attempt {attempt+1}/{policy.max_retries}): {str(e)}"
                )
                if attempt < policy.max_retries - 1:
                    await asyncio.sleep(policy.backoff_factor ** attempt)
                    
        # Fallback attempt
        logger.warning(
            f"Falling back to {policy.fallback_provider}/{policy.fallback_model} "
            f"due to {str(last_exception)}"
        )
        try:
            return await fallback.generate_response(messages, temperature, max_tokens)
        except Exception as e:
            logger.error(f"Fallback LLM ({policy.fallback_provider}/{policy.fallback_model}) failed: {str(e)}")
            raise e
