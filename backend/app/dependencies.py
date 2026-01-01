"""
Personal AI OS - Dependencies
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.services.interaction import InteractionService
from app.services.rule_engine import RuleEngineService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_interaction_service(
    db: AsyncSession
) -> InteractionService:
    """Dependency to get interaction service."""
    return InteractionService(db)


async def get_rule_engine_service(
    db: AsyncSession
) -> RuleEngineService:
    """Dependency to get rule engine service."""
    return RuleEngineService(db)
