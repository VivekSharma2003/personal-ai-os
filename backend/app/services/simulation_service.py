"""
Personal AI OS - Simulation Service

"What-if" analysis: preview how adding or editing a rule would change
AI responses without persisting any changes.
"""
from typing import Dict, Any, List
from uuid import UUID
from dataclasses import dataclass, asdict

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule
from app.core.logging import get_logger

logger = get_logger("services.simulation")


@dataclass
class SimulationResult:
    """Result of simulating a rule against a single prompt."""
    prompt: str
    response_without: str
    response_with: str
    diff_summary: str
    impact_score: float


class SimulationService:
    """Service for dry-run rule impact simulation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def simulate_rule(
        self,
        user_id: UUID,
        draft_rule_content: str,
        test_prompts: List[str],
    ) -> Dict[str, Any]:
        """
        Simulate adding a new rule.

        For each test prompt, generates a response WITH and WITHOUT
        the draft rule, then computes impact metrics.
        """
        results = []

        for prompt in test_prompts[:5]:  # Cap at 5 to control costs
            result = await self._run_comparison(
                user_id=user_id,
                prompt=prompt,
                additional_rule=draft_rule_content,
                excluded_rule_id=None,
            )
            results.append(result)

        avg_impact = sum(r.impact_score for r in results) / len(results) if results else 0

        logger.info(
            "Rule simulation completed",
            extra={"extra_data": {
                "user_id": str(user_id),
                "prompts_tested": len(results),
                "avg_impact": round(avg_impact, 3),
            }},
        )

        return {
            "simulation_type": "new_rule",
            "draft_rule": draft_rule_content,
            "prompts_tested": len(results),
            "avg_impact_score": round(avg_impact, 3),
            "results": [asdict(r) for r in results],
        }

    async def simulate_edit(
        self,
        user_id: UUID,
        rule_id: UUID,
        new_content: str,
        test_prompts: List[str],
    ) -> Dict[str, Any]:
        """
        Simulate editing an existing rule.

        Compares responses using the old rule content vs. the new content.
        """
        # Fetch the existing rule
        result = await self.db.execute(
            select(Rule).where(and_(Rule.id == rule_id, Rule.user_id == user_id))
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return {"error": "Rule not found"}

        old_content = rule.content
        results = []

        for prompt in test_prompts[:5]:
            result = await self._run_edit_comparison(
                user_id=user_id,
                prompt=prompt,
                rule_id=rule_id,
                old_content=old_content,
                new_content=new_content,
            )
            results.append(result)

        avg_impact = sum(r.impact_score for r in results) / len(results) if results else 0

        logger.info(
            "Rule edit simulation completed",
            extra={"extra_data": {
                "user_id": str(user_id),
                "rule_id": str(rule_id),
                "prompts_tested": len(results),
                "avg_impact": round(avg_impact, 3),
            }},
        )

        return {
            "simulation_type": "edit_rule",
            "rule_id": str(rule_id),
            "old_content": old_content,
            "new_content": new_content,
            "prompts_tested": len(results),
            "avg_impact_score": round(avg_impact, 3),
            "results": [asdict(r) for r in results],
        }

    async def _run_comparison(
        self,
        user_id: UUID,
        prompt: str,
        additional_rule: str,
        excluded_rule_id: UUID = None,
    ) -> SimulationResult:
        """Generate responses with and without an additional rule."""
        from app.services.prompt_builder import PromptBuilder
        from app.core.llm import call_llm

        builder = PromptBuilder(self.db)

        # Response WITHOUT the new rule (current state)
        messages_without = await builder.build_prompt(
            user_id=user_id,
            user_message=prompt,
        )
        response_without = await call_llm(
            messages=messages_without,
            temperature=0.3,
            max_tokens=512,
        )

        # Response WITH the new rule
        messages_with = await builder.build_prompt(
            user_id=user_id,
            user_message=prompt,
        )
        # Inject the draft rule into the system prompt
        if messages_with and messages_with[0]["role"] == "system":
            messages_with[0]["content"] += f"\n\nAdditional rule to follow: {additional_rule}"
        else:
            messages_with.insert(0, {
                "role": "system",
                "content": f"Follow this rule: {additional_rule}",
            })

        response_with = await call_llm(
            messages=messages_with,
            temperature=0.3,
            max_tokens=512,
        )

        # Compute impact
        impact_score = self._compute_impact(response_without, response_with)
        diff_summary = self._summarize_diff(response_without, response_with)

        return SimulationResult(
            prompt=prompt,
            response_without=response_without.strip(),
            response_with=response_with.strip(),
            diff_summary=diff_summary,
            impact_score=impact_score,
        )

    async def _run_edit_comparison(
        self,
        user_id: UUID,
        prompt: str,
        rule_id: UUID,
        old_content: str,
        new_content: str,
    ) -> SimulationResult:
        """Generate responses with old vs. new rule content."""
        from app.core.llm import call_llm

        base_system = "You are a helpful AI assistant. Follow the user's preferences."

        # Response with OLD rule
        response_old = await call_llm(
            messages=[
                {"role": "system", "content": f"{base_system}\n\nRule: {old_content}"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=512,
        )

        # Response with NEW rule
        response_new = await call_llm(
            messages=[
                {"role": "system", "content": f"{base_system}\n\nRule: {new_content}"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=512,
        )

        impact_score = self._compute_impact(response_old, response_new)
        diff_summary = self._summarize_diff(response_old, response_new)

        return SimulationResult(
            prompt=prompt,
            response_without=response_old.strip(),
            response_with=response_new.strip(),
            diff_summary=diff_summary,
            impact_score=impact_score,
        )

    def _compute_impact(self, text_a: str, text_b: str) -> float:
        """
        Compute how different two responses are (0 = identical, 1 = completely different).

        Uses 1 - Jaccard similarity.
        """
        if not text_a or not text_b:
            return 1.0
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a and not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        jaccard = len(intersection) / len(union) if union else 0
        return round(1.0 - jaccard, 3)

    def _summarize_diff(self, text_a: str, text_b: str) -> str:
        """Generate a brief diff summary."""
        words_a = set(text_a.lower().split()) if text_a else set()
        words_b = set(text_b.lower().split()) if text_b else set()

        added = words_b - words_a
        removed = words_a - words_b

        if not added and not removed:
            return "Responses are nearly identical"

        parts = []
        if added:
            sample = list(added)[:5]
            parts.append(f"+{len(added)} new terms (e.g., {', '.join(sample)})")
        if removed:
            sample = list(removed)[:5]
            parts.append(f"-{len(removed)} removed terms (e.g., {', '.join(sample)})")

        return "; ".join(parts)
