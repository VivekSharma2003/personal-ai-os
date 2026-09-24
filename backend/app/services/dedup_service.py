"""
Personal AI OS - Semantic Rule Deduplication Service

Detects rules that are semantically equivalent or highly similar so that users
can review and merge them. Similarity is computed via:
  1. Exact normalised text match (hash)
  2. Jaccard similarity on word-level trigrams (no external ML required)

For production, swap the Jaccard similarity with vector cosine similarity
against the existing pgvector embeddings.
"""
import hashlib
import logging
from itertools import combinations
from typing import List, Dict, Any, Set, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rule_engine import RuleEngineService
from app.models.rule import RuleStatus

logger = logging.getLogger(__name__)


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


def _trigrams(text: str) -> Set[str]:
    words = _normalise(text).split()
    if len(words) < 3:
        return set(words)
    return {f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words) - 2)}


def _jaccard(a: str, b: str) -> float:
    tg_a = _trigrams(a)
    tg_b = _trigrams(b)
    if not tg_a and not tg_b:
        return 1.0
    if not tg_a or not tg_b:
        return 0.0
    return len(tg_a & tg_b) / len(tg_a | tg_b)


class DedupService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_engine = RuleEngineService(db)

    async def find_duplicates(
        self,
        user_id: UUID,
        similarity_threshold: float = 0.70,
    ) -> List[Dict[str, Any]]:
        """
        Return groups of rules that are likely duplicates.

        Each group is a dict:
          {
            "rule_ids": [str, ...],
            "similarity": float,
            "reason": "exact" | "trigram",
          }
        """
        rules = await self.rule_engine.get_user_rules(
            user_id, status=RuleStatus.ACTIVE.value
        )
        if len(rules) < 2:
            return []

        groups: List[Dict[str, Any]] = []
        seen_pairs: Set[Tuple[str, str]] = set()

        for r1, r2 in combinations(rules, 2):
            pair_key = tuple(sorted([str(r1.id), str(r2.id)]))
            if pair_key in seen_pairs:
                continue

            n1 = _normalise(r1.content)
            n2 = _normalise(r2.content)

            # Exact match
            if hashlib.md5(n1.encode()).hexdigest() == hashlib.md5(n2.encode()).hexdigest():
                groups.append({
                    "rule_ids": [str(r1.id), str(r2.id)],
                    "similarity": 1.0,
                    "reason": "exact",
                    "previews": [r1.content[:80], r2.content[:80]],
                })
                seen_pairs.add(pair_key)
                continue

            # Trigram similarity
            sim = _jaccard(n1, n2)
            if sim >= similarity_threshold:
                groups.append({
                    "rule_ids": [str(r1.id), str(r2.id)],
                    "similarity": round(sim, 4),
                    "reason": "trigram",
                    "previews": [r1.content[:80], r2.content[:80]],
                })
                seen_pairs.add(pair_key)

        # Sort most similar first
        groups.sort(key=lambda g: g["similarity"], reverse=True)
        return groups

    async def merge(
        self,
        user_id: UUID,
        rule_ids: List[UUID],
        merged_content: str,
    ) -> Dict[str, Any]:
        """
        Archive the source rules and create one merged replacement.
        """
        for rid in rule_ids:
            await self.rule_engine.archive_rule(rid, reason="deduplication_merge")

        new_rule = await self.rule_engine.create_rule(
            user_id=user_id,
            content=merged_content,
            category="general",
            original_correction="Merged from duplicate detection",
        )
        await self.db.commit()
        return {
            "archived_ids": [str(rid) for rid in rule_ids],
            "new_rule_id": str(new_rule.id),
        }
