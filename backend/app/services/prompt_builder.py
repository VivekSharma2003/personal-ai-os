"""
Personal AI OS - Prompt Builder Service

Constructs optimized prompts with rules and context.
"""
from typing import List, Dict, Optional
from uuid import UUID

from app.core.prompts import build_system_prompt, build_rules_section
from app.db.redis import ConversationCache


class PromptBuilderService:
    """Service for building LLM prompts with user rules and context."""
    
    def __init__(self):
        pass
    
    async def build_chat_prompt(
        self,
        user_message: str,
        rules: List[dict],
        conversation_id: Optional[str] = None,
        include_history: bool = True,
        db: Optional[object] = None,
        profile_id: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> List[Dict[str, str]]:
        """
        Build a complete chat prompt with rules and conversation history.
        """
        system_preamble = ""
        filtered_rules = [dict(r) for r in rules]  # Create copy of rule dicts to avoid mutating cache

        # Resolve variables and model configs if DB session is active
        if db:
            try:
                from uuid import UUID
                from app.services.variable_service import VariableService
                from app.services.rule_model_config_service import RuleModelConfigService
                from app.config import get_settings

                resolved_user_id = user_id
                if not resolved_user_id and filtered_rules:
                    first_rule = filtered_rules[0]
                    if "user_id" in first_rule and first_rule["user_id"]:
                        resolved_user_id = UUID(first_rule["user_id"])

                if resolved_user_id:
                    # 1. Resolve variables
                    var_service = VariableService(db)
                    filtered_rules = await var_service.resolve_rules(resolved_user_id, filtered_rules)

                    # 2. Resolve model-specific optimized content
                    settings = get_settings()
                    provider = settings.llm_provider
                    model_name = settings.openai_model if provider == "openai" else (
                        settings.gemini_model if provider == "gemini" else settings.anthropic_model
                    )

                    config_service = RuleModelConfigService(db)
                    rule_ids = [UUID(r["id"]) for r in filtered_rules if "id" in r and r["id"]]
                    
                    if rule_ids:
                        active_overrides = await config_service.get_active_overrides(rule_ids, provider, model_name)
                        for r_dict in filtered_rules:
                            if "id" in r_dict and r_dict["id"]:
                                r_uuid = UUID(r_dict["id"])
                                if r_uuid in active_overrides and active_overrides[r_uuid].optimized_content:
                                    r_dict["content"] = active_overrides[r_uuid].optimized_content
            except Exception:
                pass

        if profile_id and db:
            try:
                from app.services.profile_service import ProfileService
                from uuid import UUID
                profile_service = ProfileService(db)
                profile_result = await profile_service.apply_profile(UUID(profile_id), filtered_rules)
                filtered_rules = profile_result["filtered_rules"]
                system_preamble = profile_result["system_preamble"]
            except Exception:
                pass

        messages = []
        
        # System prompt with rules
        system_prompt = build_system_prompt(filtered_rules)
        if system_preamble:
            system_prompt = f"{system_preamble}\n\n{system_prompt}"

        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history if available
        if include_history and conversation_id:
            history = await ConversationCache.get_context(conversation_id)
            if history:
                for msg in history[-10:]:  # Last 10 messages for context
                    messages.append(msg)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def build_rules_only_prompt(self, rules: List[dict]) -> str:
        """
        Build just the rules section for inspection.
        
        Args:
            rules: List of rule dicts
        
        Returns:
            Formatted rules section string
        """
        return build_rules_section(rules)
    
    async def update_conversation_context(
        self,
        conversation_id: str,
        user_message: str,
        assistant_response: str
    ):
        """
        Update the conversation context in cache.
        
        Args:
            conversation_id: The conversation ID
            user_message: The user's message
            assistant_response: The AI's response
        """
        await ConversationCache.append_message(
            conversation_id,
            {"role": "user", "content": user_message}
        )
        await ConversationCache.append_message(
            conversation_id,
            {"role": "assistant", "content": assistant_response}
        )
    
    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate token count for a list of messages.
        
        Uses rough approximation of ~4 characters per token.
        
        Args:
            messages: List of message dicts
        
        Returns:
            Estimated token count
        """
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4
    
    def truncate_for_context(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4000
    ) -> List[Dict[str, str]]:
        """
        Truncate messages to fit within token limit.
        
        Preserves system prompt and recent messages.
        
        Args:
            messages: List of message dicts
            max_tokens: Maximum token limit
        
        Returns:
            Truncated list of messages
        """
        if not messages:
            return messages
        
        # Always keep system prompt
        system_prompt = messages[0] if messages[0]["role"] == "system" else None
        other_messages = messages[1:] if system_prompt else messages
        
        result = [system_prompt] if system_prompt else []
        current_tokens = self.estimate_tokens(result)
        
        # Add messages from most recent, respecting limit
        for msg in reversed(other_messages):
            msg_tokens = len(msg.get("content", "")) // 4
            if current_tokens + msg_tokens > max_tokens:
                break
            result.insert(1 if system_prompt else 0, msg)
            current_tokens += msg_tokens
        
        return result
