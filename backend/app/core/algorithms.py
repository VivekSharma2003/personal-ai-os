"""
Personal AI OS - Core Algorithms

Implements confidence calculation, decay, rule ranking, and similarity detection.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import numpy as np

from app.config import get_settings


settings = get_settings()


def calculate_confidence(
    base_confidence: float = 0.5,
    times_reinforced: int = 0,
    last_applied_at: Optional[datetime] = None,
    last_reinforced_at: Optional[datetime] = None
) -> float:
    """
    Calculate the current confidence score for a rule.
    
    Formula: confidence = base + reinforcement_bonus - decay_penalty
    
    Args:
        base_confidence: Starting confidence (default 0.5)
        times_reinforced: Number of times rule was reinforced
        last_applied_at: When the rule was last applied
        last_reinforced_at: When the rule was last reinforced
    
    Returns:
        Confidence score between 0.1 and 0.95
    """
    # Reinforcement bonus: +0.1 per reinforcement, capped at +0.45
    reinforcement_bonus = min(times_reinforced * 0.1, 0.45)
    
    # Calculate decay based on time since last use
    decay_penalty = 0.0
    if last_applied_at:
        days_since_use = (datetime.utcnow() - last_applied_at).days
        weeks_unused = days_since_use // 7
        # -0.05 per week unused, capped at 0.4
        decay_penalty = min(weeks_unused * settings.decay_rate, 0.4)
    
    # Calculate final confidence
    confidence = base_confidence + reinforcement_bonus - decay_penalty
    
    # Clamp between 0.1 and 0.95
    return max(0.1, min(0.95, confidence))


def calculate_decay(
    current_confidence: float,
    last_applied_at: Optional[datetime] = None
) -> float:
    """
    Calculate the decay amount for a rule.
    
    Args:
        current_confidence: Current confidence score
        last_applied_at: When the rule was last applied
    
    Returns:
        Decay amount to subtract from confidence
    """
    if not last_applied_at:
        return 0.0
    
    days_since_use = (datetime.utcnow() - last_applied_at).days
    
    # No decay for rules used in the last week
    if days_since_use < 7:
        return 0.0
    
    # Decay rate increases with time
    weeks_unused = days_since_use // 7
    return min(weeks_unused * settings.decay_rate, current_confidence - 0.1)


def should_archive_rule(confidence: float) -> bool:
    """
    Determine if a rule should be archived based on its confidence.
    
    Args:
        confidence: Current confidence score
    
    Returns:
        True if the rule should be archived
    """
    return confidence < settings.archive_threshold


def rank_rules(
    rules: List[dict],
    context_embedding: Optional[List[float]] = None,
    max_rules: int = 10
) -> List[Tuple[dict, float]]:
    """
    Rank rules by relevance to the current context.
    
    Score = confidence * relevance * recency_boost
    
    Args:
        rules: List of rule dicts with 'confidence', 'embedding', 'last_applied_at'
        context_embedding: Embedding of the current context
        max_rules: Maximum number of rules to return
    
    Returns:
        List of (rule, score) tuples, sorted by score descending
    """
    now = datetime.utcnow()
    scored_rules = []
    
    for rule in rules:
        confidence = rule.get("confidence", 0.5)
        
        # Calculate relevance via cosine similarity
        relevance = 1.0  # Default if no embeddings
        if context_embedding and rule.get("embedding"):
            relevance = cosine_similarity(
                context_embedding,
                rule["embedding"]
            )
        
        # Recency boost: 1.2x if used in last 24 hours
        recency_boost = 1.0
        last_applied = rule.get("last_applied_at")
        if last_applied:
            if isinstance(last_applied, str):
                last_applied = datetime.fromisoformat(last_applied)
            if (now - last_applied) < timedelta(hours=24):
                recency_boost = 1.2
        
        # Calculate final score
        score = confidence * relevance * recency_boost
        
        # Only include rules above threshold
        if confidence >= settings.confidence_threshold:
            scored_rules.append((rule, score))
    
    # Sort by score and limit
    scored_rules.sort(key=lambda x: x[1], reverse=True)
    return scored_rules[:max_rules]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
    
    Returns:
        Similarity score between 0 and 1
    """
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    dot_product = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def find_similar_rule(
    new_rule_embedding: List[float],
    existing_rules: List[dict],
    threshold: float = None
) -> Optional[dict]:
    """
    Find a semantically similar rule in the existing rules.
    
    Used for duplicate detection and rule merging.
    
    Args:
        new_rule_embedding: Embedding of the new rule
        existing_rules: List of rule dicts with 'embedding' key
        threshold: Similarity threshold (default from settings)
    
    Returns:
        The similar rule if found, None otherwise
    """
    threshold = threshold or settings.similarity_threshold
    
    for rule in existing_rules:
        if rule.get("embedding"):
            similarity = cosine_similarity(new_rule_embedding, rule["embedding"])
            if similarity >= threshold:
                return rule
    
    return None


def merge_rules(existing_rule: dict, new_correction: str) -> dict:
    """
    Merge a new correction into an existing rule.
    
    This reinforces the existing rule and may update its content.
    
    Args:
        existing_rule: The existing rule to merge into
        new_correction: The new correction text
    
    Returns:
        Updated rule dict
    """
    return {
        **existing_rule,
        "times_reinforced": existing_rule.get("times_reinforced", 0) + 1,
        "last_reinforced_at": datetime.utcnow().isoformat(),
        "confidence": min(0.95, existing_rule.get("confidence", 0.5) + 0.1)
    }


def select_rules_for_prompt(
    rules: List[dict],
    context_embedding: Optional[List[float]] = None,
    max_tokens: int = 500
) -> List[dict]:
    """
    Select rules to include in the prompt, respecting token limits.
    
    Args:
        rules: All active rules for the user
        context_embedding: Embedding of current context for relevance
        max_tokens: Approximate token budget for rules
    
    Returns:
        Selected rules to include in prompt
    """
    # Rank by relevance and confidence
    ranked = rank_rules(rules, context_embedding)
    
    selected = []
    estimated_tokens = 0
    
    for rule, score in ranked:
        # Rough token estimate: ~1 token per 4 characters
        rule_tokens = len(rule.get("content", "")) // 4
        
        if estimated_tokens + rule_tokens > max_tokens:
            break
        
        selected.append(rule)
        estimated_tokens += rule_tokens
    
    return selected
