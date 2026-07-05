"""
Personal AI OS - Experiment Service

Manages A/B testing of rule variants with statistical significance.
"""
import random
import math
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experiment import Experiment
from app.models.rule import Rule, RuleStatus
from app.core.logging import get_logger

logger = get_logger("services.experiment")


class ExperimentService:
    """Service for managing rule A/B tests."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_experiment(
        self,
        user_id: UUID,
        name: str,
        rule_a_id: UUID,
        rule_b_id: UUID,
        min_sample_size: int = 50,
    ) -> Experiment:
        """Create a new A/B experiment between two rule variants."""
        # Validate both rules exist and belong to user
        rule_a = await self.db.get(Rule, rule_a_id)
        rule_b = await self.db.get(Rule, rule_b_id)

        if not rule_a or not rule_b:
            raise ValueError("One or both rule IDs are invalid")
        if rule_a.user_id != user_id or rule_b.user_id != user_id:
            raise ValueError("Both rules must belong to the user")
        if rule_a_id == rule_b_id:
            raise ValueError("Cannot A/B test a rule against itself")

        experiment = Experiment(
            user_id=user_id,
            name=name,
            rule_a_id=rule_a_id,
            rule_b_id=rule_b_id,
            min_sample_size=min_sample_size,
        )
        self.db.add(experiment)
        await self.db.flush()

        logger.info(f"Created experiment '{name}'", extra={"extra_data": {
            "experiment_id": str(experiment.id),
            "rule_a": str(rule_a_id),
            "rule_b": str(rule_b_id),
        }})

        return experiment

    async def assign_variant(self, experiment_id: UUID) -> str:
        """
        Randomly assign a variant (a or b) for this interaction.
        Increments the corresponding impression counter.

        Returns "a" or "b".
        """
        experiment = await self.db.get(Experiment, experiment_id)
        if not experiment or experiment.status != "running":
            raise ValueError("Experiment not found or not running")

        variant = random.choice(["a", "b"])

        if variant == "a":
            experiment.variant_a_impressions += 1
        else:
            experiment.variant_b_impressions += 1

        await self.db.flush()
        return variant

    async def record_outcome(
        self,
        experiment_id: UUID,
        variant: str,
        positive: bool,
    ) -> Dict[str, Any]:
        """
        Record a user satisfaction signal for a variant.

        Args:
            experiment_id: Experiment ID
            variant: "a" or "b"
            positive: True = positive signal, False = negative

        Returns:
            Updated experiment stats.
        """
        experiment = await self.db.get(Experiment, experiment_id)
        if not experiment:
            raise ValueError("Experiment not found")
        if variant not in ("a", "b"):
            raise ValueError("Variant must be 'a' or 'b'")

        if positive:
            if variant == "a":
                experiment.variant_a_positive += 1
            else:
                experiment.variant_b_positive += 1

        await self.db.flush()

        # Check if we should auto-evaluate
        total = experiment.variant_a_impressions + experiment.variant_b_impressions
        if total >= experiment.min_sample_size and experiment.status == "running":
            await self._evaluate(experiment)

        return experiment.to_dict()

    async def evaluate_experiment(self, experiment_id: UUID) -> Dict[str, Any]:
        """Manually evaluate an experiment for a winner."""
        experiment = await self.db.get(Experiment, experiment_id)
        if not experiment:
            raise ValueError("Experiment not found")
        await self._evaluate(experiment)
        return experiment.to_dict()

    async def _evaluate(self, experiment: Experiment):
        """
        Evaluate the experiment using a simple proportion z-test.
        Declares a winner if p < 0.05 and both variants have minimum impressions.
        """
        n_a = experiment.variant_a_impressions
        n_b = experiment.variant_b_impressions

        if n_a < 10 or n_b < 10:
            return  # Not enough data

        p_a = experiment.variant_a_positive / n_a if n_a > 0 else 0
        p_b = experiment.variant_b_positive / n_b if n_b > 0 else 0

        # Pooled proportion
        p_pool = (experiment.variant_a_positive + experiment.variant_b_positive) / (n_a + n_b)

        if p_pool == 0 or p_pool == 1:
            return  # Cannot compute z-score

        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n_a + 1/n_b))

        if se == 0:
            return

        z = (p_a - p_b) / se
        # Two-tailed p-value approximation
        p_value = 2 * (1 - self._normal_cdf(abs(z)))

        if p_value < 0.05:
            experiment.winner = "a" if p_a > p_b else "b"
            experiment.status = "completed"
            experiment.completed_at = datetime.utcnow()

            logger.info(f"Experiment '{experiment.name}' concluded", extra={"extra_data": {
                "winner": experiment.winner,
                "p_value": round(p_value, 4),
                "rate_a": round(p_a * 100, 1),
                "rate_b": round(p_b * 100, 1),
            }})

            await self.db.flush()

    @staticmethod
    def _normal_cdf(x: float) -> float:
        """Approximate the normal CDF using the error function."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    async def list_experiments(self, user_id: UUID) -> List[Dict[str, Any]]:
        """List all experiments for a user."""
        q = select(Experiment).where(
            Experiment.user_id == user_id
        ).order_by(Experiment.created_at.desc())
        result = await self.db.execute(q)
        return [e.to_dict() for e in result.scalars().all()]

    async def get_experiment(self, experiment_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a single experiment by ID."""
        experiment = await self.db.get(Experiment, experiment_id)
        return experiment.to_dict() if experiment else None

    async def pause_experiment(self, experiment_id: UUID) -> Dict[str, Any]:
        """Pause or resume an experiment."""
        experiment = await self.db.get(Experiment, experiment_id)
        if not experiment:
            raise ValueError("Experiment not found")

        if experiment.status == "running":
            experiment.status = "paused"
        elif experiment.status == "paused":
            experiment.status = "running"
        else:
            raise ValueError("Cannot pause/resume a completed experiment")

        await self.db.flush()
        return experiment.to_dict()

    async def conclude_experiment(
        self,
        experiment_id: UUID,
    ) -> Dict[str, Any]:
        """
        Finalize an experiment: apply the winning rule (activate it),
        archive the losing rule.
        """
        experiment = await self.db.get(Experiment, experiment_id)
        if not experiment:
            raise ValueError("Experiment not found")

        # Force evaluation if not yet done
        if not experiment.winner:
            await self._evaluate(experiment)

        if not experiment.winner:
            # Still no winner — determine by raw rate
            n_a = experiment.variant_a_impressions
            n_b = experiment.variant_b_impressions
            p_a = experiment.variant_a_positive / n_a if n_a > 0 else 0
            p_b = experiment.variant_b_positive / n_b if n_b > 0 else 0
            experiment.winner = "a" if p_a >= p_b else "b"

        experiment.status = "completed"
        experiment.completed_at = datetime.utcnow()

        # Apply winner / archive loser
        winner_rule_id = experiment.rule_a_id if experiment.winner == "a" else experiment.rule_b_id
        loser_rule_id = experiment.rule_b_id if experiment.winner == "a" else experiment.rule_a_id

        winner = await self.db.get(Rule, winner_rule_id)
        loser = await self.db.get(Rule, loser_rule_id)

        if winner:
            winner.status = RuleStatus.ACTIVE.value
            winner.confidence = min(1.0, winner.confidence + 0.1)
        if loser:
            loser.status = RuleStatus.ARCHIVED.value

        await self.db.flush()

        logger.info(f"Experiment '{experiment.name}' concluded and applied", extra={"extra_data": {
            "winner": experiment.winner,
            "winner_rule_id": str(winner_rule_id),
            "loser_rule_id": str(loser_rule_id),
        }})

        return experiment.to_dict()
