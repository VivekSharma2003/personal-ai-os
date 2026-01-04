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
        include_history: bool = True
    ) -> List[Dict[str, str]]:
        """
        Build a complete chat prompt with rules and conversation history.
        
        Args:
            user_message: The current user message
            rules: List of rule dicts to apply
            conversation_id: Optional conversation ID for history
            include_history: Whether to include conversation history
        
        Returns:
            List of message dicts ready for the LLM
        """
        messages = []
        
        # System prompt with rules
        system_prompt = build_system_prompt(rules)
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
