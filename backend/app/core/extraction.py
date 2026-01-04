"""
Personal AI OS - Rule Extraction Logic
"""
import json
from typing import Optional, Tuple
from datetime import datetime

from app.core.llm import extract_json_response, generate_embedding, evaluate_relevance
from app.core.prompts import (
    RULE_EXTRACTION_PROMPT, 
    CORRECTION_DETECTION_PROMPT,
    RULE_EVALUATION_PROMPT
)
from app.core.algorithms import find_similar_rule, cosine_similarity
from app.config import get_settings


settings = get_settings()


async def detect_correction(
    user_message: str,
    previous_response: str
) -> Tuple[bool, str, float]:
    """
    Detect if a user message is a correction to the previous AI response.
    
    Args:
        user_message: The user's message
        previous_response: The AI's previous response
    
    Returns:
        Tuple of (is_correction, correction_type, confidence)
    """
    prompt = CORRECTION_DETECTION_PROMPT.format(
        previous_response=previous_response[:1000],  # Truncate for token efficiency
        user_message=user_message
    )
    
    try:
        result = await extract_json_response(prompt)
        return (
            result.get("is_correction", False),
            result.get("correction_type", "none"),
            result.get("confidence", 0.0)
        )
    except Exception as e:
        # If LLM fails, fall back to simple heuristics
        correction_keywords = [
            "don't", "dont", "stop", "never", "always", 
            "instead", "rather", "prefer", "please use",
            "not like", "wrong", "fix", "change"
        ]
        is_correction = any(kw in user_message.lower() for kw in correction_keywords)
        return (is_correction, "style" if is_correction else "none", 0.5 if is_correction else 0.0)


async def extract_rule(
    user_correction: str,
    previous_response: str
) -> Optional[dict]:
    """
    Extract a reusable rule from a user correction.
    
    Args:
        user_correction: The user's correction/feedback
        previous_response: The AI's previous response that was corrected
    
    Returns:
        Dict with rule content, category, and reasoning, or None if extraction fails
    """
    prompt = RULE_EXTRACTION_PROMPT.format(
        previous_response=previous_response[:1000],
        user_correction=user_correction
    )
    
    try:
        result = await extract_json_response(prompt)
        
        if not result.get("is_valid", True):
            return None
        
        rule_content = result.get("rule")
        if not rule_content:
            return None
        
        return {
            "content": rule_content,
            "category": result.get("category", "style"),
            "reasoning": result.get("reasoning", ""),
            "original_correction": user_correction,
            "created_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Rule extraction failed: {e}")
        return None


async def check_rule_relevance(
    rule_content: str,
    rule_category: str,
    user_message: str
) -> Tuple[bool, float]:
    """
    Check if a rule is relevant to the current user message.
    
    Args:
        rule_content: The rule to evaluate
        rule_category: The rule's category
        user_message: The current user message
    
    Returns:
        Tuple of (is_relevant, confidence)
    """
    prompt = RULE_EVALUATION_PROMPT.format(
        rule_content=rule_content,
        rule_category=rule_category,
        user_message=user_message[:500]
    )
    
    try:
        result = await extract_json_response(prompt)
        return (
            result.get("is_relevant", False),
            result.get("confidence", 0.0)
        )
    except Exception:
        # Fall back to always applying high-confidence rules
        return (True, 0.5)


async def check_duplicate_rule(
    new_rule_content: str,
    existing_rules: list
) -> Optional[dict]:
    """
    Check if a similar rule already exists.
    
    Uses semantic similarity via embeddings.
    
    Args:
        new_rule_content: The content of the new rule
        existing_rules: List of existing rule dicts with embeddings
    
    Returns:
        The similar existing rule if found, None otherwise
    """
    try:
        new_embedding = await generate_embedding(new_rule_content)
        return find_similar_rule(new_embedding, existing_rules)
    except Exception as e:
        print(f"Duplicate check failed: {e}")
        return None


async def process_correction(
    user_correction: str,
    previous_response: str,
    existing_rules: list
) -> dict:
    """
    Full pipeline for processing a user correction.
    
    1. Extract rule from correction
    2. Check for duplicates
    3. Generate embedding
    4. Return rule data ready for storage
    
    Args:
        user_correction: The user's correction
        previous_response: The AI's previous response
        existing_rules: User's existing rules for duplicate detection
    
    Returns:
        Dict with status and rule data
    """
    # Step 1: Extract rule
    rule_data = await extract_rule(user_correction, previous_response)
    
    if not rule_data:
        return {
            "status": "extraction_failed",
            "message": "Could not extract a clear rule from this correction"
        }
    
    # Step 2: Check for duplicates
    duplicate = await check_duplicate_rule(rule_data["content"], existing_rules)
    
    if duplicate:
        return {
            "status": "duplicate_found",
            "existing_rule": duplicate,
            "message": "This preference already exists and has been reinforced"
        }
    
    # Step 3: Generate embedding for the new rule
    try:
        embedding = await generate_embedding(rule_data["content"])
        rule_data["embedding"] = embedding
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        rule_data["embedding"] = None
    
    # Step 4: Return new rule data
    return {
        "status": "rule_created",
        "rule": rule_data,
        "message": f"✓ Learned preference: {rule_data['content']}"
    }
