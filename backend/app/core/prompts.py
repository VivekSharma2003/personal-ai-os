"""
Personal AI OS - Prompt Templates
"""

# System prompt template for rule application
SYSTEM_PROMPT_TEMPLATE = """You are a helpful AI assistant. Follow these rules strictly:

{rules_section}

Instructions:
- Apply all rules above without mentioning them unless explicitly asked
- Maintain a natural, helpful tone
- If a rule conflicts with the user's explicit request, prioritize the request
- Be consistent in applying preferences across all responses"""


# Rule extraction prompt
RULE_EXTRACTION_PROMPT = """Analyze this user correction and extract a reusable rule.

CONTEXT:
Previous AI response: {previous_response}
User correction: {user_correction}

TASK:
1. Identify the specific preference being expressed
2. Generalize it into a reusable rule
3. Categorize it: style | tone | formatting | logic | safety

OUTPUT (JSON):
{{
    "rule": "The generalized, reusable rule in imperative form (e.g., 'Use bullet points for lists')",
    "category": "category_name",
    "reasoning": "Brief explanation of why this rule was extracted",
    "is_valid": true/false
}}

GUIDELINES:
- Be specific but generalizable
- Focus on actionable instructions
- Write rules in imperative form ("Do X", "Avoid Y")
- Avoid over-generalizing from a single instance
- If the correction is too vague or context-specific, set is_valid to false"""


# Rule self-evaluation prompt
RULE_EVALUATION_PROMPT = """Evaluate if this rule should be applied to the current context.

RULE: {rule_content}
CATEGORY: {rule_category}
USER MESSAGE: {user_message}

Determine if this rule is relevant to the current context.

OUTPUT (JSON):
{{
    "is_relevant": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}}

Consider:
- Does the context match the rule's domain?
- Would applying this rule improve the response?
- Is there any conflict with the user's current request?"""


# Correction detection prompt
CORRECTION_DETECTION_PROMPT = """Analyze if this user message is a correction or feedback about the previous AI response.

PREVIOUS AI RESPONSE: {previous_response}
USER MESSAGE: {user_message}

Determine if the user is:
1. Correcting something the AI did wrong
2. Expressing a preference for future responses
3. Providing feedback on style, tone, or formatting
4. Just continuing the conversation normally

OUTPUT (JSON):
{{
    "is_correction": true/false,
    "correction_type": "style" | "tone" | "formatting" | "logic" | "safety" | "none",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}}"""


# Rule conflict detection prompt
RULE_CONFLICT_PROMPT = """Analyze if these two rules conflict with each other.

RULE 1: {rule1}
RULE 2: {rule2}

OUTPUT (JSON):
{{
    "conflicts": true/false,
    "explanation": "Brief explanation of conflict or compatibility",
    "resolution": "If conflicting, which rule should take precedence and why"
}}"""


def build_rules_section(rules: list) -> str:
    """
    Build a token-efficient rules section for the system prompt.
    
    Groups rules by category and formats them as bullet points.
    
    Args:
        rules: List of Rule objects or dicts with 'content' and 'category'
    
    Returns:
        Formatted rules section string
    """
    if not rules:
        return "No specific preferences to apply."
    
    # Group by category
    categorized = {}
    for rule in rules:
        category = rule.get("category") if isinstance(rule, dict) else rule.category
        content = rule.get("content") if isinstance(rule, dict) else rule.content
        
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(content)
    
    # Format sections
    sections = []
    category_order = ["safety", "logic", "formatting", "style", "tone"]
    
    for category in category_order:
        if category in categorized:
            items = categorized[category]
            section = f"[{category.upper()}]\n" + "\n".join(f"• {r}" for r in items)
            sections.append(section)
    
    # Add any remaining categories
    for category, items in categorized.items():
        if category not in category_order:
            section = f"[{category.upper()}]\n" + "\n".join(f"• {r}" for r in items)
            sections.append(section)
    
    return "\n\n".join(sections)


def build_system_prompt(rules: list) -> str:
    """
    Build the complete system prompt with rules.
    
    Args:
        rules: List of Rule objects or dicts
    
    Returns:
        Complete system prompt string
    """
    rules_section = build_rules_section(rules)
    return SYSTEM_PROMPT_TEMPLATE.format(rules_section=rules_section)
