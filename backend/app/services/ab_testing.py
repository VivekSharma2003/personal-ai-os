"""
Personal AI OS - A/B Prompt Testing Service

Allows creating prompt variants and tracking which version yields better outcomes.
"""
import logging
import random
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.ab_experiment import ABExperiment, ABVariant, ABResult

logger = logging.getLogger(__name__)

class ABTestingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_experiment(
        self,
        user_id: UUID,
        name: str,
        variants: List[Dict[str, str]]
    ) -> ABExperiment:
        """Create a new A/B experiment with N variants."""
        experiment = ABExperiment(user_id=user_id, name=name)
        self.db.add(experiment)
        await self.db.flush()

        for v in variants:
            variant = ABVariant(
                experiment_id=experiment.id,
                label=v["label"],
                prompt_template=v["prompt_template"]
            )
            self.db.add(variant)

        await self.db.commit()
        await self.db.refresh(experiment)
        return experiment

    async def select_variant(self, experiment_id: UUID) -> Optional[ABVariant]:
        """Randomly select a variant to serve (uniform distribution)."""
        result = await self.db.execute(
            select(ABVariant).where(ABVariant.experiment_id == experiment_id)
        )
        variants = result.scalars().all()
        if not variants:
            return None
        return random.choice(variants)

    async def record_result(
        self,
        variant_id: UUID,
        user_id: UUID,
        score: float,
        feedback: Optional[str] = None
    ) -> ABResult:
        """Record a user outcome/score for a variant."""
        res = ABResult(
            variant_id=variant_id,
            user_id=user_id,
            score=score,
            feedback=feedback
        )
        self.db.add(res)
        await self.db.commit()
        await self.db.refresh(res)
        return res

    async def get_experiment_stats(self, experiment_id: UUID) -> List[Dict[str, Any]]:
        """Return avg score and response count per variant."""
        result = await self.db.execute(
            select(
                ABVariant.id,
                ABVariant.label,
                func.count(ABResult.id).label("responses"),
                func.avg(ABResult.score).label("avg_score"),
            )
            .join(ABResult, ABResult.variant_id == ABVariant.id, isouter=True)
            .where(ABVariant.experiment_id == experiment_id)
            .group_by(ABVariant.id, ABVariant.label)
        )
        rows = result.all()
        return [
            {
                "variant_id": str(r.id),
                "label": r.label,
                "responses": r.responses,
                "avg_score": round(float(r.avg_score), 4) if r.avg_score else None,
            }
            for r in rows
        ]
