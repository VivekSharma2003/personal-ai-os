"""
Personal AI OS - Replay Service

Replays past interactions against the current rule set to detect
regressions or improvements after rule changes.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Interaction
from app.models.replay import ReplayRun, ReplayResult
from app.core.logging import get_logger

logger = get_logger("services.replay")


class ReplayService:
    """Service for prompt replay and regression testing."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_replay(
        self,
        user_id: UUID,
        name: str,
        interaction_ids: List[str] = None,
        sample_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Start a replay run.

        If interaction_ids is provided, replays those specific interactions.
        Otherwise, samples the most recent `sample_size` interactions.
        """
        if interaction_ids:
            ids = [UUID(iid) for iid in interaction_ids]
            result = await self.db.execute(
                select(Interaction).where(
                    and_(
                        Interaction.user_id == user_id,
                        Interaction.id.in_(ids),
                    )
                )
            )
        else:
            result = await self.db.execute(
                select(Interaction)
                .where(Interaction.user_id == user_id)
                .order_by(desc(Interaction.created_at))
                .limit(sample_size)
            )

        interactions = list(result.scalars().all())
        if not interactions:
            return {"error": "No interactions found to replay"}

        # Create run
        run = ReplayRun(
            id=uuid4(),
            user_id=user_id,
            name=name,
            status="running",
            total_interactions=len(interactions),
        )
        self.db.add(run)
        await self.db.flush()

        # Process each interaction
        for interaction in interactions:
            await self._process_replay_item(run, interaction)

        # Finalize run
        run.status = "completed"
        run.completed_at = datetime.utcnow()

        logger.info(
            "Replay run completed",
            extra={"extra_data": {
                "run_id": str(run.id),
                "total": run.total_interactions,
                "regressions": run.regressions_found,
                "improvements": run.improvements_found,
            }},
        )

        return run.to_dict()

    async def _process_replay_item(
        self, run: ReplayRun, interaction: Interaction
    ) -> None:
        """Re-generate response for a single interaction with current rules."""
        from app.services.prompt_builder import PromptBuilder
        from app.core.llm import call_llm

        try:
            # Build prompt with current rules
            builder = PromptBuilder(self.db)
            messages = await builder.build_prompt(
                user_id=run.user_id,
                user_message=interaction.user_message,
            )

            # Generate new response
            replayed_response = await call_llm(
                messages=messages,
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=1024,
            )

            # Compute similarity (simple word overlap Jaccard)
            similarity = self._compute_similarity(
                interaction.assistant_response, replayed_response
            )

            # Classify verdict
            if similarity >= 0.85:
                verdict = "unchanged"
                run.unchanged_count = (run.unchanged_count or 0) + 1
            elif similarity < 0.85:
                # Use LLM to classify if it's a regression or improvement
                verdict = await self._classify_change(
                    interaction.user_message,
                    interaction.assistant_response,
                    replayed_response,
                )
                if verdict == "regression":
                    run.regressions_found = (run.regressions_found or 0) + 1
                else:
                    run.improvements_found = (run.improvements_found or 0) + 1

            # Generate diff summary
            diff_summary = self._generate_diff_summary(
                interaction.assistant_response, replayed_response
            )

            result = ReplayResult(
                id=uuid4(),
                run_id=run.id,
                interaction_id=interaction.id,
                original_prompt=interaction.user_message,
                original_response=interaction.assistant_response,
                replayed_response=replayed_response,
                similarity_score=similarity,
                verdict=verdict,
                diff_summary=diff_summary,
            )
            self.db.add(result)

        except Exception as e:
            logger.error(
                f"Replay item failed: {e}",
                extra={"extra_data": {
                    "run_id": str(run.id),
                    "interaction_id": str(interaction.id),
                }},
            )
            result = ReplayResult(
                id=uuid4(),
                run_id=run.id,
                interaction_id=interaction.id,
                original_prompt=interaction.user_message,
                original_response=interaction.assistant_response,
                replayed_response=f"[Error: {str(e)}]",
                similarity_score=0.0,
                verdict="regression",
                diff_summary=f"Processing error: {str(e)}",
            )
            self.db.add(result)
            run.regressions_found = (run.regressions_found or 0) + 1

        run.completed = (run.completed or 0) + 1

    def _compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute Jaccard word overlap similarity between two texts."""
        if not text_a or not text_b:
            return 0.0
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a and not words_b:
            return 1.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    async def _classify_change(
        self, prompt: str, original: str, replayed: str
    ) -> str:
        """Use LLM to classify whether a change is a regression or improvement."""
        from app.core.llm import call_llm

        try:
            classification = await call_llm(
                messages=[{
                    "role": "user",
                    "content": (
                        "Given a user prompt and two AI responses (original and new), "
                        "classify whether the new response is an IMPROVEMENT or REGRESSION "
                        "compared to the original. Respond with exactly one word: "
                        "'improvement' or 'regression'.\n\n"
                        f"User prompt: {prompt[:200]}\n"
                        f"Original response: {original[:300]}\n"
                        f"New response: {replayed[:300]}"
                    ),
                }],
                temperature=0.1,
                max_tokens=10,
            )
            verdict = classification.strip().lower()
            return verdict if verdict in ("improvement", "regression") else "regression"
        except Exception:
            return "regression"

    def _generate_diff_summary(self, original: str, replayed: str) -> str:
        """Generate a brief diff summary."""
        orig_words = set(original.lower().split()) if original else set()
        new_words = set(replayed.lower().split()) if replayed else set()

        added = new_words - orig_words
        removed = orig_words - new_words

        parts = []
        if added:
            parts.append(f"+{len(added)} new terms")
        if removed:
            parts.append(f"-{len(removed)} removed terms")
        if not parts:
            parts.append("No significant differences")

        return "; ".join(parts)

    async def list_runs(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> Dict[str, Any]:
        """List replay runs for a user."""
        count_q = await self.db.execute(
            select(func.count()).select_from(ReplayRun).where(
                ReplayRun.user_id == user_id
            )
        )
        total = count_q.scalar() or 0

        result = await self.db.execute(
            select(ReplayRun)
            .where(ReplayRun.user_id == user_id)
            .order_by(desc(ReplayRun.created_at))
            .limit(limit)
            .offset(offset)
        )
        runs = [r.to_dict() for r in result.scalars().all()]

        return {"total": total, "limit": limit, "offset": offset, "runs": runs}

    async def get_run(self, run_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a single replay run detail."""
        result = await self.db.execute(
            select(ReplayRun).where(ReplayRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        return run.to_dict() if run else None

    async def get_results(
        self, run_id: UUID, verdict_filter: str = None, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """Get detailed results for a replay run."""
        stmt = select(ReplayResult).where(ReplayResult.run_id == run_id)

        if verdict_filter:
            stmt = stmt.where(ReplayResult.verdict == verdict_filter)

        count_q = await self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_q.scalar() or 0

        stmt = stmt.order_by(ReplayResult.similarity_score.asc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        results = [r.to_dict() for r in result.scalars().all()]

        return {"total": total, "limit": limit, "offset": offset, "results": results}
