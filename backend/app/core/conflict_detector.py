"""
Personal AI OS - Conflict Detection Engine

LLM-powered pairwise conflict analysis between rules.
Uses embeddings for fast pre-filtering, then LLM for precise assessment.
"""
from typing import List, Dict, Any, Optional, Tuple
from itertools import combinations

from app.core.llm import extract_json_response, generate_embedding
from app.core.algorithms import cosine_similarity
from app.config import get_settings


settings = get_settings()

# Prompt for pairwise conflict detection
CONFLICT_DETECTION_PROMPT = """Analyze whether these two user preference rules conflict with each other.

RULE A: {rule_a}
RULE B: {rule_b}

Two rules conflict if:
- They give contradictory instructions (e.g., "use formal tone" vs "keep it casual")
- Following both simultaneously would produce an inconsistent response
- They specify opposite behaviors for the same aspect of a response

Two rules do NOT conflict if:
- They address different aspects of responses
- They complement each other
- They can both be followed simultaneously without contradiction

Respond with a JSON object:
{{
    "conflicts": true/false,
    "severity": 0.0-1.0,
    "explanation": "Clear explanation of the conflict or why they are compatible",
    "suggested_resolution": "keep_both" | "keep_newer" | "keep_older" | "merge" | "disable_one",
    "merged_rule": "If suggesting merge, provide the merged rule text. Otherwise null."
}}"""


async def detect_pairwise_conflict(
    rule_a_content: str,
    rule_b_content: str
) -> Dict[str, Any]:
    """
    Detect if two rules conflict using LLM analysis.

    Args:
        rule_a_content: Content of the first rule
        rule_b_content: Content of the second rule

    Returns:
        Dict with conflicts, severity, explanation, and suggested_resolution
    """
    prompt = CONFLICT_DETECTION_PROMPT.format(
        rule_a=rule_a_content,
        rule_b=rule_b_content
    )

    try:
        result = await extract_json_response(
            prompt=prompt,
            system_prompt="You are a rule analysis expert. Detect conflicts between user preference rules. Respond ONLY with valid JSON."
        )
        return {
            "conflicts": result.get("conflicts", False),
            "severity": min(max(float(result.get("severity", 0.5)), 0.0), 1.0),
            "explanation": result.get("explanation", ""),
            "suggested_resolution": result.get("suggested_resolution", "keep_both"),
            "merged_rule": result.get("merged_rule"),
        }
    except Exception as e:
        print(f"Conflict detection LLM call failed: {e}")
        return {
            "conflicts": False,
            "severity": 0.0,
            "explanation": f"Analysis failed: {e}",
            "suggested_resolution": "keep_both",
            "merged_rule": None,
        }


async def prefilter_potential_conflicts(
    target_rule: dict,
    candidate_rules: List[dict],
    similarity_threshold: float = 0.6
) -> List[dict]:
    """
    Pre-filter rules by semantic similarity to reduce LLM calls.

    Rules that address completely unrelated topics are unlikely to conflict.
    We keep rules with moderate-to-high similarity for LLM analysis since
    conflicts often arise between rules in the same domain.

    Args:
        target_rule: The rule to check against others
        candidate_rules: List of other rule dicts
        similarity_threshold: Min similarity to consider for conflict check

    Returns:
        Filtered list of candidate rules that could potentially conflict
    """
    target_content = target_rule.get("content", "")

    try:
        target_embedding = await generate_embedding(target_content)
    except Exception:
        # If embedding fails, return all candidates for LLM check
        return candidate_rules

    candidates = []
    for rule in candidate_rules:
        # Skip self
        if rule.get("id") == target_rule.get("id"):
            continue

        # Try to get embedding for comparison
        rule_content = rule.get("content", "")
        try:
            rule_embedding = await generate_embedding(rule_content)
            similarity = cosine_similarity(target_embedding, rule_embedding)

            if similarity >= similarity_threshold:
                candidates.append(rule)
        except Exception:
            # Include rules we can't compare
            candidates.append(rule)

    return candidates


async def scan_all_conflicts(
    rules: List[dict],
    similarity_threshold: float = 0.6
) -> List[Dict[str, Any]]:
    """
    Scan all rule pairs for conflicts.

    Uses embedding pre-filtering to reduce O(n²) LLM calls.

    Args:
        rules: List of rule dicts with 'id' and 'content'
        similarity_threshold: Pre-filter threshold

    Returns:
        List of detected conflicts with rule IDs and details
    """
    if len(rules) < 2:
        return []

    conflicts = []

    # Pre-compute embeddings for all rules
    embeddings = {}
    for rule in rules:
        try:
            embeddings[rule["id"]] = await generate_embedding(rule["content"])
        except Exception:
            embeddings[rule["id"]] = None

    # Check all pairs, pre-filtered by similarity
    for rule_a, rule_b in combinations(rules, 2):
        # Pre-filter: check semantic similarity
        emb_a = embeddings.get(rule_a["id"])
        emb_b = embeddings.get(rule_b["id"])

        if emb_a is not None and emb_b is not None:
            similarity = cosine_similarity(emb_a, emb_b)
            if similarity < similarity_threshold:
                continue  # Too dissimilar to conflict

        # LLM analysis for potential conflicts
        result = await detect_pairwise_conflict(rule_a["content"], rule_b["content"])

        if result["conflicts"]:
            conflicts.append({
                "rule_a_id": rule_a["id"],
                "rule_b_id": rule_b["id"],
                "rule_a_content": rule_a["content"],
                "rule_b_content": rule_b["content"],
                **result,
            })

    return conflicts
