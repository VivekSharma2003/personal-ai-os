"""
Personal AI OS - Suggestions Service

Analyzes recent interactions to suggest new rules using LLM.
"""
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Interaction
from app.models.rule import Rule, RuleStatus
from app.core.llm import extract_json_response


SUGGESTION_PROMPT = """You are analyzing a user's recent AI chat interactions to identify patterns 
that could become useful rules/preferences.

Here are the user's recent interactions (user message -> AI response pairs):

{interactions}

Here are the user's EXISTING rules (avoid duplicates):

{existing_rules}

Analyze these interactions for implicit preferences or patterns. Look for:
- Consistent style preferences (code formatting, response length, tone)
- Repeated types of requests
- Patterns in how the user phrases things
- Topics or domains the user frequently explores

Generate 0-5 rule suggestions. Each suggestion should be:
- A clear, actionable preference rule
- Not a duplicate of existing rules
- Supported by evidence from the interactions

Respond with a JSON object:
{{
    "suggestions": [
        {{
            "content": "The suggested rule text",
            "category": "style|tone|formatting|logic|safety",
            "confidence": 0.0-1.0,
            "reason": "Why this rule is suggested",
            "example": "Brief example from the interactions"
        }}
    ]
}}

If no clear patterns are found, return {{"suggestions": []}}."""


class SuggestionService:
    """Service for generating AI-powered rule suggestions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_suggestions(
        self,
        user_id: UUID,
        max_interactions: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze recent interactions and generate rule suggestions.

        Args:
            user_id: Internal UUID of the user
            max_interactions: Number of recent interactions to analyze

        Returns:
            Dict with suggestions list and metadata
        """
        # Get recent uncorrected interactions
        result = await self.db.execute(
            select(Interaction)
            .where(Interaction.user_id == user_id)
            .order_by(Interaction.created_at.desc())
            .limit(max_interactions)
        )
        interactions = list(result.scalars().all())

        if len(interactions) < 3:
            return {
                "suggestions": [],
                "total": 0,
                "interactions_analyzed": len(interactions),
            }

        # Get existing rules to avoid duplicates
        rules_result = await self.db.execute(
            select(Rule)
            .where(Rule.user_id == user_id)
            .where(Rule.status == RuleStatus.ACTIVE.value)
        )
        existing_rules = list(rules_result.scalars().all())

        # Format interactions for the prompt
        interactions_text = "\n".join([
            f"[{i + 1}] User: {inter.user_message[:200]}\n    AI: {inter.assistant_response[:200]}"
            for i, inter in enumerate(interactions[:20])  # Limit for token budget
        ])

        existing_rules_text = "\n".join([
            f"- [{r.category}] {r.content}"
            for r in existing_rules
        ]) or "(No existing rules)"

        # Call LLM for suggestions
        prompt = SUGGESTION_PROMPT.format(
            interactions=interactions_text,
            existing_rules=existing_rules_text,
        )

        try:
            llm_result = await extract_json_response(
                prompt=prompt,
                system_prompt="You are a pattern analysis assistant. Analyze chat interactions and suggest user preference rules. Respond ONLY with valid JSON."
            )

            raw_suggestions = llm_result.get("suggestions", [])

            suggestions = []
            for s in raw_suggestions[:5]:  # Cap at 5
                suggestions.append({
                    "content": s.get("content", ""),
                    "category": s.get("category", "style"),
                    "confidence": min(max(float(s.get("confidence", 0.5)), 0.0), 1.0),
                    "reason": s.get("reason", ""),
                    "example_interaction": s.get("example", None),
                    "times_observed": 1,
                })

            return {
                "suggestions": suggestions,
                "total": len(suggestions),
                "interactions_analyzed": len(interactions),
            }

        except Exception as e:
            print(f"Rule suggestion generation failed: {e}")
            return {
                "suggestions": [],
                "total": 0,
                "interactions_analyzed": len(interactions),
            }
