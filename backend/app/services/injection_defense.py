"""
Personal AI OS - Prompt Injection Defense Service
"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class InjectionDefenseService:
    """
    Evaluates prompts for adversarial prompt injection or jailbreak attempts.
    """
    
    # Common jailbreak phrases and adversarial heuristics
    BLOCKLIST = [
        "ignore all previous instructions",
        "forget all previous instructions",
        "disregard previous instructions",
        "system prompt override",
        "you are now a",
        "developer mode enabled",
        "dan mode",
        "do anything now"
    ]

    def __init__(self, active: bool = True):
        self.active = active

    def evaluate_prompt(self, prompt: str) -> Tuple[bool, str]:
        """
        Evaluates a user prompt. 
        Returns (is_safe, reason).
        """
        if not self.active or not prompt:
            return True, ""
            
        prompt_lower = prompt.lower()
        
        for phrase in self.BLOCKLIST:
            if phrase in prompt_lower:
                logger.warning(f"Prompt injection detected. Matched blocked phrase: '{phrase}'")
                return False, f"Malicious input detected: Attempted system override or jailbreak ('{phrase}')."
                
        return True, ""
