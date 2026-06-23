"""
Personal AI OS - LLM Cost Tracker

Pricing table for token cost estimation and utility functions
for capturing usage from LLM provider responses.
"""
from typing import Tuple

from app.core.logging import get_logger

logger = get_logger("core.cost_tracker")


# Pricing per 1K tokens: (prompt_price, completion_price)
# Updated pricing as of 2025. Adjust as providers change rates.
PRICING_TABLE: dict[str, dict[str, Tuple[float, float]]] = {
    "openai": {
        "gpt-4-turbo-preview":  (0.01, 0.03),
        "gpt-4-turbo":          (0.01, 0.03),
        "gpt-4o":               (0.005, 0.015),
        "gpt-4o-mini":          (0.00015, 0.0006),
        "gpt-4":                (0.03, 0.06),
        "gpt-3.5-turbo":       (0.0005, 0.0015),
        # Embedding models (prompt only, no completion)
        "text-embedding-3-small": (0.00002, 0.0),
        "text-embedding-3-large": (0.00013, 0.0),
    },
    "gemini": {
        "gemini-1.5-pro":       (0.00125, 0.005),
        "gemini-1.5-flash":     (0.000075, 0.0003),
        "gemini-2.0-flash":     (0.0001, 0.0004),
        "gemini-2.5-pro":       (0.00125, 0.01),
        "gemini-2.5-flash":     (0.000075, 0.0003),
        # Embedding
        "text-embedding-004":   (0.000025, 0.0),
    },
    "anthropic": {
        "claude-3-5-sonnet-20241022": (0.003, 0.015),
        "claude-3-opus-20240229":     (0.015, 0.075),
        "claude-3-haiku-20240307":    (0.00025, 0.00125),
        "claude-sonnet-4-20250514":   (0.003, 0.015),
        "claude-opus-4-20250516":     (0.015, 0.075),
    },
}

# Fallback pricing for unknown models
DEFAULT_PRICING: Tuple[float, float] = (0.005, 0.015)


def compute_cost(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    Compute estimated cost in USD for an LLM call.

    Args:
        provider: LLM provider name (openai, gemini, anthropic)
        model: Model identifier
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens

    Returns:
        Estimated cost in USD
    """
    provider_lower = provider.lower()
    model_lower = model.lower()

    pricing = DEFAULT_PRICING
    if provider_lower in PRICING_TABLE:
        provider_pricing = PRICING_TABLE[provider_lower]
        # Try exact match, then prefix match
        if model_lower in provider_pricing:
            pricing = provider_pricing[model_lower]
        else:
            for known_model, price in provider_pricing.items():
                if model_lower.startswith(known_model) or known_model.startswith(model_lower):
                    pricing = price
                    break

    prompt_cost = (prompt_tokens / 1000.0) * pricing[0]
    completion_cost = (completion_tokens / 1000.0) * pricing[1]

    return round(prompt_cost + completion_cost, 8)


def estimate_tokens_from_text(text: str) -> int:
    """
    Rough token estimation from text length.
    Uses ~4 characters per token heuristic.
    """
    return max(1, len(text) // 4)
