"""
Personal AI OS - Self-Healing Service

Uses LLM to judge rule adherence and suggest edits to self-heal/refine violated rules.
"""
from typing import Dict, Any, List
from uuid import UUID, uuid4
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adherence_eval import AdherenceEvaluation
from app.models.interaction import Interaction
from app.models.rule import Rule
from app.services.versioning import VersioningService
from app.core.llm import call_llm
from app.core.logging import get_logger

logger = get_logger("services.self_healing")


class SelfHealingService:
    """Service to evaluate rule adherence and self-heal violated rules."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate_interaction(self, interaction_id: UUID) -> Dict[str, Any]:
        """Judge whether the assistant's response adhered to all applied rules in an interaction."""
        stmt = select(Interaction).where(Interaction.id == interaction_id)
        result = await self.db.execute(stmt)
        interaction = result.scalar_one_or_none()

        if not interaction:
            return {"error": "Interaction not found"}

        if not interaction.rules_applied:
            return {"message": "No rules were applied in this interaction", "evaluations": []}

        # Fetch the rules applied
        rules_stmt = select(Rule).where(Rule.id.in_(interaction.rules_applied))
        rules_result = await self.db.execute(rules_stmt)
        rules = rules_result.scalars().all()

        evaluations = []

        for rule in rules:
            # LLM Prompt to judge rule adherence
            judge_prompt = (
                "You are an objective AI compliance judge. Evaluate whether the assistant's response "
                "complied with the given user preference rule.\n\n"
                f"Rule to follow: \"{rule.content}\"\n"
                f"User input message: \"{interaction.user_message}\"\n"
                f"Assistant response: \"{interaction.assistant_response}\"\n\n"
                "Provide your evaluation in the following format:\n"
                "Adhered: Yes/No\n"
                "Score: [Float between 0.0 and 1.0 representing how well the rule was followed]\n"
                "Justification: [Brief explanation of compliance or violation]"
            )

            try:
                raw_judge = await call_llm(
                    messages=[{"role": "user", "content": judge_prompt}],
                    temperature=0.1,
                    max_tokens=256,
                )

                # Parse judge output
                adhered = "adhered: yes" in raw_judge.lower()
                score = 1.0
                justification = raw_judge

                # Try parsing values
                score_match = [line for line in raw_judge.split("\n") if "score:" in line.lower()]
                if score_match:
                    try:
                        score = float(score_match[0].split(":")[-1].strip())
                    except ValueError:
                        pass

                just_match = [line for line in raw_judge.split("\n") if "justification:" in line.lower()]
                if just_match:
                    justification = just_match[0].split(":")[-1].strip()

                # Save evaluation
                evaluation = AdherenceEvaluation(
                    id=uuid4(),
                    interaction_id=interaction_id,
                    rule_id=rule.id,
                    adhered=adhered,
                    score=score,
                    justification=justification,
                )
                self.db.add(evaluation)

                evaluations.append(evaluation.to_dict())

            except Exception as e:
                logger.error(f"Failed to run LLM judge on rule {rule.id}: {e}")
                continue

        await self.db.flush()
        return {"interaction_id": str(interaction_id), "evaluations": evaluations}

    async def get_adherence_stats(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get average adherence score and count of evaluations per rule."""
        stmt = (
            select(
                Rule.id,
                Rule.content,
                func.count(AdherenceEvaluation.id).label("eval_count"),
                func.avg(AdherenceEvaluation.score).label("avg_score"),
            )
            .join(AdherenceEvaluation, Rule.id == AdherenceEvaluation.rule_id)
            .where(Rule.user_id == user_id)
            .group_by(Rule.id, Rule.content)
            .order_by(desc("avg_score"))
        )
        result = await self.db.execute(stmt)

        stats = []
        for row in result.all():
            stats.append(
                {
                    "rule_id": str(row[0]),
                    "content": row[1],
                    "eval_count": row[2],
                    "avg_score": round(row[3], 2) if row[3] is not None else 1.0,
                }
            )
        return stats

    async def heal_rule(self, rule_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        Check evaluations for a rule. If adherence is low, call LLM to suggest
        a refined (self-healed) version of the rule.
        """
        # Fetch rule
        rule_check = await self.db.execute(
            select(Rule).where(and_(Rule.id == rule_id, Rule.user_id == user_id))
        )
        rule = rule_check.scalar_one_or_none()
        if not rule:
            return {"error": "Rule not found or unauthorized"}

        # Fetch recent evaluations
        eval_stmt = (
            select(AdherenceEvaluation)
            .where(AdherenceEvaluation.rule_id == rule_id)
            .order_by(desc(AdherenceEvaluation.created_at))
            .limit(5)
        )
        eval_result = await self.db.execute(eval_stmt)
        evals = eval_result.scalars().all()

        if not evals:
            return {"message": "No evaluations recorded for this rule yet. Cannot self-heal."}

        avg_score = sum(e.score for e in evals) / len(evals)

        violations = [e.justification for e in evals if not e.adhered]
        violations_summary = "\n".join(f"- {v}" for v in violations[:3])

        # Self-healing is only triggered if average score is < 0.8 or there is at least one violation
        if avg_score >= 0.8 and not violations:
            return {
                "message": "Rule adherence is healthy. No healing needed.",
                "adherence_score": round(avg_score, 2),
            }

        # Prompt to rewrite the rule to make it clearer/harder to violate
        heal_prompt = (
            "You are a prompt engineering and compliance expert. A system rule has been frequently "
            "violated by the assistant. Suggest a clearer, more explicit, and stricter rewrite of the rule "
            "to prevent these violations.\n\n"
            f"Original Rule: \"{rule.content}\"\n"
            f"Observed compliance issues/violations:\n{violations_summary}\n\n"
            "Return ONLY the rewritten rule text, nothing else. Make it concise and actionable."
        )

        suggested_content = await call_llm(
            messages=[{"role": "user", "content": heal_prompt}],
            temperature=0.3,
            max_tokens=256,
        )

        suggested_content = suggested_content.strip()

        # Create Rule Version snapshot before updating rule
        versioning = VersioningService(self.db)
        await versioning.create_version(
            rule=rule,
            change_reason="Self-healing refinement due to rule violations",
            changed_by="system",
        )

        # Update rule content
        old_content = rule.content
        rule.content = suggested_content

        await self.db.flush()

        logger.info(f"Self-healed rule {rule_id}: '{old_content}' -> '{suggested_content}'")

        return {
            "healed": True,
            "rule_id": str(rule_id),
            "old_content": old_content,
            "new_content": suggested_content,
            "adherence_score": round(avg_score, 2),
        }
