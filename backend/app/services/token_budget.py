"""
Personal AI OS - Prompt Token Budget Enforcer Service

Estimates token count for a prompt and enforces per-model context window limits.
Uses a fast heuristic (word-count × 1.35) that matches OpenAI's rule of thumb
without requiring tiktoken as a hard dependency.

For production use, swap `_estimate_tokens` with a tiktoken call.
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Max context windows by provider:model (input tokens only, leaving room for output)
MODEL_LIMITS: Dict[str, int] = {
    "openai:gpt-4o":              100_000,
    "openai:gpt-4-turbo":         100_000,
    "openai:gpt-3.5-turbo":         12_000,
    "anthropic:claude-3-opus":    180_000,
    "anthropic:claude-3-sonnet":  180_000,
    "anthropic:claude-3-haiku":   180_000,
    "google:gemini-1.5-pro":    1_000_000,
    "google:gemini-1.0-pro":       28_000,
    # fallback for unknown models
    "_default":                    16_000,
}


def _estimate_tokens(text: str) -> int:
    """Heuristic: words × 1.35 ≈ tokens for English prose."""
    words = len(text.split())
    return max(1, int(words * 1.35))


class TokenBudgetService:
    """
    Validates and trims prompts to stay within model context windows.
    """

    def get_limit(self, provider: str, model: str) -> int:
        key = f"{provider}:{model}"
        return MODEL_LIMITS.get(key, MODEL_LIMITS["_default"])

    def estimate(self, text: str) -> int:
        return _estimate_tokens(text)

    def check(
        self,
        provider: str,
        model: str,
        prompt: str,
        reserved_output_tokens: int = 1024,
    ) -> Dict:
        """
        Returns a dict with:
          - estimated_tokens: int
          - limit: int (model context window)
          - available: int (limit - reserved_output_tokens)
          - within_budget: bool
          - overflow: int (tokens over budget, 0 if within)
        """
        limit = self.get_limit(provider, model)
        available = max(0, limit - reserved_output_tokens)
        estimated = _estimate_tokens(prompt)
        overflow = max(0, estimated - available)

        return {
            "estimated_tokens": estimated,
            "limit": limit,
            "available": available,
            "within_budget": overflow == 0,
            "overflow": overflow,
        }

    def truncate(
        self,
        provider: str,
        model: str,
        prompt: str,
        reserved_output_tokens: int = 1024,
        truncation_marker: str = "\n\n[...truncated to fit context window...]",
    ) -> str:
        """
        Trim *prompt* word-by-word from the end until it fits in the budget.
        Appends a truncation marker so callers know the prompt was shortened.
        """
        report = self.check(provider, model, prompt, reserved_output_tokens)
        if report["within_budget"]:
            return prompt

        available = report["available"]
        marker_tokens = _estimate_tokens(truncation_marker)
        budget = max(0, available - marker_tokens)
        words = prompt.split()

        while words and _estimate_tokens(" ".join(words)) > budget:
            words.pop()

        truncated = " ".join(words) + truncation_marker
        logger.warning(
            f"Prompt truncated for {provider}/{model}: "
            f"{report['estimated_tokens']} → {_estimate_tokens(truncated)} tokens"
        )
        return truncated
