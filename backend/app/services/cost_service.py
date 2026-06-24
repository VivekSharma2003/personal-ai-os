"""
Personal AI OS - Cost Service

Per-user LLM usage tracking, budget enforcement, and cost analytics.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_usage import LLMUsage
from app.core.cost_tracker import compute_cost
from app.core.logging import get_logger
from app.config import get_settings

logger = get_logger("services.cost")


class CostService:
    """Service for tracking LLM costs and enforcing budget limits."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_usage(
        self,
        user_id: UUID,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        endpoint: str = "chat",
    ) -> LLMUsage:
        """
        Record a single LLM call's token usage and computed cost.

        Returns the created LLMUsage record.
        """
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = compute_cost(provider, model, prompt_tokens, completion_tokens)

        usage = LLMUsage(
            user_id=user_id,
            provider=provider,
            model=model,
            endpoint=endpoint,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
        )
        self.db.add(usage)
        await self.db.flush()

        logger.info(
            f"Recorded LLM usage: {provider}/{model} {total_tokens} tokens ${estimated_cost:.6f}",
            extra={"extra_data": {
                "user_id": str(user_id),
                "provider": provider,
                "model": model,
                "total_tokens": total_tokens,
                "cost_usd": estimated_cost,
            }},
        )

        return usage

    async def get_usage_summary(
        self,
        user_id: UUID,
        period: str = "month",
    ) -> Dict[str, Any]:
        """
        Get aggregated usage summary for a time period.

        Args:
            user_id: User ID
            period: "day", "week", or "month"

        Returns:
            Summary dict with totals and per-provider/model breakdown.
        """
        cutoff = self._period_cutoff(period)

        # Total aggregation
        totals_q = select(
            func.count(LLMUsage.id).label("total_requests"),
            func.coalesce(func.sum(LLMUsage.prompt_tokens), 0).label("total_prompt_tokens"),
            func.coalesce(func.sum(LLMUsage.completion_tokens), 0).label("total_completion_tokens"),
            func.coalesce(func.sum(LLMUsage.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(LLMUsage.estimated_cost_usd), 0.0).label("total_cost"),
        ).where(
            and_(LLMUsage.user_id == user_id, LLMUsage.created_at >= cutoff)
        )
        totals_result = await self.db.execute(totals_q)
        totals = totals_result.one()

        # Per-provider breakdown
        provider_q = select(
            LLMUsage.provider,
            func.count(LLMUsage.id).label("requests"),
            func.coalesce(func.sum(LLMUsage.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(LLMUsage.estimated_cost_usd), 0.0).label("cost"),
        ).where(
            and_(LLMUsage.user_id == user_id, LLMUsage.created_at >= cutoff)
        ).group_by(LLMUsage.provider)
        provider_result = await self.db.execute(provider_q)
        providers = [
            {"provider": row.provider, "requests": row.requests, "tokens": row.tokens, "cost": round(row.cost, 6)}
            for row in provider_result.all()
        ]

        # Per-model breakdown
        model_q = select(
            LLMUsage.provider,
            LLMUsage.model,
            func.count(LLMUsage.id).label("requests"),
            func.coalesce(func.sum(LLMUsage.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(LLMUsage.estimated_cost_usd), 0.0).label("cost"),
        ).where(
            and_(LLMUsage.user_id == user_id, LLMUsage.created_at >= cutoff)
        ).group_by(LLMUsage.provider, LLMUsage.model)
        model_result = await self.db.execute(model_q)
        models = [
            {
                "provider": row.provider,
                "model": row.model,
                "requests": row.requests,
                "tokens": row.tokens,
                "cost": round(row.cost, 6),
            }
            for row in model_result.all()
        ]

        return {
            "period": period,
            "since": cutoff.isoformat(),
            "total_requests": totals.total_requests,
            "total_prompt_tokens": totals.total_prompt_tokens,
            "total_completion_tokens": totals.total_completion_tokens,
            "total_tokens": totals.total_tokens,
            "total_cost_usd": round(totals.total_cost, 6),
            "by_provider": providers,
            "by_model": models,
        }

    async def get_cost_trend(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get daily cost time-series for the last N days.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        q = select(
            func.date(LLMUsage.created_at).label("date"),
            func.count(LLMUsage.id).label("requests"),
            func.coalesce(func.sum(LLMUsage.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(LLMUsage.estimated_cost_usd), 0.0).label("cost"),
        ).where(
            and_(LLMUsage.user_id == user_id, LLMUsage.created_at >= cutoff)
        ).group_by(
            func.date(LLMUsage.created_at)
        ).order_by(
            func.date(LLMUsage.created_at)
        )

        result = await self.db.execute(q)
        return [
            {
                "date": str(row.date),
                "requests": row.requests,
                "tokens": row.tokens,
                "cost": round(row.cost, 6),
            }
            for row in result.all()
        ]

    async def get_cost_breakdown(
        self,
        user_id: UUID,
        period: str = "month",
    ) -> Dict[str, Any]:
        """
        Per-endpoint breakdown (chat, stream, extract, feedback).
        """
        cutoff = self._period_cutoff(period)

        q = select(
            LLMUsage.endpoint,
            func.count(LLMUsage.id).label("requests"),
            func.coalesce(func.sum(LLMUsage.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(LLMUsage.estimated_cost_usd), 0.0).label("cost"),
        ).where(
            and_(LLMUsage.user_id == user_id, LLMUsage.created_at >= cutoff)
        ).group_by(LLMUsage.endpoint)

        result = await self.db.execute(q)
        endpoints = [
            {
                "endpoint": row.endpoint,
                "requests": row.requests,
                "tokens": row.tokens,
                "cost": round(row.cost, 6),
            }
            for row in result.all()
        ]

        return {"period": period, "since": cutoff.isoformat(), "by_endpoint": endpoints}

    async def get_budget(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get current budget limits and remaining quota.
        Uses system defaults from config; per-user overrides could be stored in Redis.
        """
        settings = get_settings()
        daily_limit = settings.llm_budget_daily_usd
        monthly_limit = settings.llm_budget_monthly_usd

        # Get today's spend
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_q = select(
            func.coalesce(func.sum(LLMUsage.estimated_cost_usd), 0.0)
        ).where(
            and_(LLMUsage.user_id == user_id, LLMUsage.created_at >= today_start)
        )
        daily_result = await self.db.execute(daily_q)
        daily_spend = daily_result.scalar() or 0.0

        # Get this month's spend
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_q = select(
            func.coalesce(func.sum(LLMUsage.estimated_cost_usd), 0.0)
        ).where(
            and_(LLMUsage.user_id == user_id, LLMUsage.created_at >= month_start)
        )
        monthly_result = await self.db.execute(monthly_q)
        monthly_spend = monthly_result.scalar() or 0.0

        return {
            "daily_limit_usd": daily_limit,
            "monthly_limit_usd": monthly_limit,
            "daily_spend_usd": round(daily_spend, 6),
            "monthly_spend_usd": round(monthly_spend, 6),
            "daily_remaining_usd": round(max(0, daily_limit - daily_spend), 6),
            "monthly_remaining_usd": round(max(0, monthly_limit - monthly_spend), 6),
            "daily_exceeded": daily_spend >= daily_limit,
            "monthly_exceeded": monthly_spend >= monthly_limit,
        }

    async def check_budget(self, user_id: UUID) -> Dict[str, Any]:
        """
        Pre-flight budget check. Returns budget status.
        Raises no exception; caller decides how to handle exceeded state.
        """
        budget = await self.get_budget(user_id)
        budget["allowed"] = not budget["daily_exceeded"] and not budget["monthly_exceeded"]
        return budget

    def _period_cutoff(self, period: str) -> datetime:
        """Convert period string to datetime cutoff."""
        now = datetime.utcnow()
        if period == "day":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            return now - timedelta(days=7)
        elif period == "month":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return now - timedelta(days=30)
