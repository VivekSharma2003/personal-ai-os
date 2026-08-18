"""
Personal AI OS - Cost Optimizer Service
"""
import logging
from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rule import Rule, RuleStatus
from app.services.rule_engine import RuleEngineService

logger = logging.getLogger(__name__)

class CostOptimizerService:
    """
    Optimizes system costs and context token sizes by dynamically 
    pruning rules based on relevance, efficiency, and context limits.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_engine = RuleEngineService(db)

    def estimate_tokens(self, text: str) -> int:
        """Simple approximation of token count."""
        if not text:
            return 0
        return max(1, len(text) // 4)
        
    def calculate_rule_efficiency(self, rule: Rule) -> float:
        """
        Calculate an efficiency score for a rule.
        Higher is better.
        """
        tokens = self.estimate_tokens(rule.content)
        
        # Base impact score from confidence and usage
        impact = rule.confidence * 10
        if rule.times_applied > 0:
            impact += min(20, rule.times_applied * 0.5)
            
        # Recent usage gives a boost
        impact += rule.times_reinforced * 2
        
        return impact / (tokens + 1)

    async def review_savings(self, user_id: UUID) -> Dict[str, Any]:
        """
        Review active rules and calculate potential savings by pruning low-efficiency rules.
        """
        rules = await self.rule_engine.get_user_rules(user_id=user_id, status=RuleStatus.ACTIVE.value)
        
        total_tokens = sum(self.estimate_tokens(r.content) for r in rules)
        
        scored_rules = []
        for r in rules:
            score = self.calculate_rule_efficiency(r)
            scored_rules.append({
                "id": r.id,
                "tokens": self.estimate_tokens(r.content),
                "score": score,
                "rule": r
            })
            
        # Sort by lowest score first
        scored_rules.sort(key=lambda x: x["score"])
        
        # Identify the bottom 20% or rules with very low scores to suggest for pruning
        prunable_candidates = []
        for item in scored_rules:
            if item["score"] < 0.5 or (len(prunable_candidates) < len(rules) * 0.2 and item["score"] < 2.0):
                prunable_candidates.append(item)
                
        savings_tokens = sum(item["tokens"] for item in prunable_candidates)
        
        return {
            "total_active_rules": len(rules),
            "total_estimated_tokens": total_tokens,
            "prunable_rules_count": len(prunable_candidates),
            "potential_savings_tokens": savings_tokens,
            "prunable_candidates": [
                {
                    "id": str(item["id"]),
                    "content": item["rule"].content,
                    "score": round(item["score"], 2),
                    "tokens": item["tokens"]
                }
                for item in prunable_candidates
            ]
        }

    async def prune_rules(self, user_id: UUID, max_tokens: int) -> Dict[str, Any]:
        """
        Takes a set of rules and drops the least efficient ones until we fit under max_tokens.
        Returns the accepted rules and what was dropped.
        """
        rules = await self.rule_engine.get_user_rules(user_id=user_id, status=RuleStatus.ACTIVE.value)
        
        scored_rules = []
        for r in rules:
            score = self.calculate_rule_efficiency(r)
            scored_rules.append({
                "rule": r,
                "tokens": self.estimate_tokens(r.content),
                "score": score
            })
            
        # Sort by score descending (highest efficiency first)
        scored_rules.sort(key=lambda x: x["score"], reverse=True)
        
        accepted = []
        dropped = []
        current_tokens = 0
        
        for item in scored_rules:
            if current_tokens + item["tokens"] <= max_tokens:
                accepted.append(item["rule"])
                current_tokens += item["tokens"]
            else:
                dropped.append(item["rule"])
                
        return {
            "accepted_rules_count": len(accepted),
            "dropped_rules_count": len(dropped),
            "total_tokens": current_tokens,
            "accepted_rules": [str(r.id) for r in accepted],
            "dropped_rules": [str(r.id) for r in dropped]
        }
