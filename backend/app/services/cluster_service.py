"""
Personal AI OS - Cluster Service

Groups semantically similar rules into clusters using FAISS vector
similarity and provides merge capabilities via LLM.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rule import Rule
from app.models.rule_cluster import RuleCluster, rule_cluster_members
from app.core.logging import get_logger
from app.config import get_settings

logger = get_logger("services.cluster")


class ClusterService:
    """Service for generating and managing rule similarity clusters."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_clusters(
        self, user_id: UUID, similarity_threshold: float = None
    ) -> Dict[str, Any]:
        """
        Generate clusters of similar rules for a user.

        1. Fetch all active rules with embeddings
        2. Compute pairwise similarity via FAISS
        3. Group rules above threshold using union-find
        4. Persist clusters to DB (replacing old ones)
        """
        settings = get_settings()
        threshold = similarity_threshold or settings.cluster_similarity_threshold

        # Fetch active rules
        result = await self.db.execute(
            select(Rule).where(
                and_(Rule.user_id == user_id, Rule.status == "active")
            )
        )
        rules = list(result.scalars().all())

        if len(rules) < 2:
            return {"clusters_created": 0, "message": "Need at least 2 active rules to cluster"}

        # Compute pairwise similarities using FAISS
        from app.db.vector import search_similar

        rule_map = {str(r.id): r for r in rules}
        adjacency: Dict[str, set] = {str(r.id): set() for r in rules}

        for rule in rules:
            if not rule.embedding_id:
                continue
            try:
                similar = await search_similar(rule.embedding_id, top_k=len(rules))
                for sim_id, score in similar:
                    if sim_id != rule.embedding_id and score >= threshold:
                        # Map embedding_id back to rule
                        for r in rules:
                            if r.embedding_id == sim_id:
                                adjacency[str(rule.id)].add(str(r.id))
                                adjacency[str(r.id)].add(str(rule.id))
            except Exception:
                continue

        # Union-find clustering
        parent = {rid: rid for rid in adjacency}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for rid, neighbors in adjacency.items():
            for nid in neighbors:
                union(rid, nid)

        # Group by root
        groups: Dict[str, List[str]] = {}
        for rid in adjacency:
            root = find(rid)
            groups.setdefault(root, []).append(rid)

        # Filter to clusters with 2+ members
        clusters_data = {k: v for k, v in groups.items() if len(v) >= 2}

        # Delete old clusters for this user
        old_clusters = await self.db.execute(
            select(RuleCluster.id).where(RuleCluster.user_id == user_id)
        )
        old_ids = [row[0] for row in old_clusters.fetchall()]
        if old_ids:
            await self.db.execute(
                delete(rule_cluster_members).where(
                    rule_cluster_members.c.cluster_id.in_(old_ids)
                )
            )
            await self.db.execute(
                delete(RuleCluster).where(RuleCluster.user_id == user_id)
            )

        # Create new clusters
        created = []
        for i, (_, member_ids) in enumerate(clusters_data.items(), 1):
            member_rules = [rule_map[mid] for mid in member_ids if mid in rule_map]
            categories = list(set(r.category for r in member_rules))
            cat_label = categories[0] if len(categories) == 1 else "mixed"

            cluster = RuleCluster(
                id=uuid4(),
                user_id=user_id,
                name=f"{cat_label.title()} Cluster #{i}",
                description=f"Auto-generated cluster of {len(member_rules)} similar {cat_label} rules",
                rule_count=len(member_rules),
                avg_similarity=threshold,
            )
            self.db.add(cluster)
            await self.db.flush()

            # Add members
            for rule in member_rules:
                await self.db.execute(
                    rule_cluster_members.insert().values(
                        cluster_id=cluster.id,
                        rule_id=rule.id,
                        similarity_to_centroid=threshold,
                    )
                )

            created.append(cluster.to_dict())

        logger.info(
            "Clusters generated",
            extra={"extra_data": {
                "user_id": str(user_id),
                "total_rules": len(rules),
                "clusters_created": len(created),
            }},
        )

        return {
            "clusters_created": len(created),
            "total_rules_clustered": sum(c["rule_count"] for c in created),
            "clusters": created,
        }

    async def list_clusters(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> Dict[str, Any]:
        """List all clusters for a user with pagination."""
        # Count
        count_q = await self.db.execute(
            select(func.count()).select_from(RuleCluster).where(
                RuleCluster.user_id == user_id
            )
        )
        total = count_q.scalar() or 0

        # Fetch
        result = await self.db.execute(
            select(RuleCluster)
            .where(RuleCluster.user_id == user_id)
            .order_by(RuleCluster.rule_count.desc())
            .limit(limit)
            .offset(offset)
        )
        clusters = [c.to_dict() for c in result.scalars().all()]

        return {"total": total, "limit": limit, "offset": offset, "clusters": clusters}

    async def get_cluster_detail(self, cluster_id: UUID) -> Optional[Dict[str, Any]]:
        """Get cluster detail with member rules."""
        result = await self.db.execute(
            select(RuleCluster)
            .options(selectinload(RuleCluster.rules))
            .where(RuleCluster.id == cluster_id)
        )
        cluster = result.scalar_one_or_none()
        if not cluster:
            return None

        data = cluster.to_dict()
        data["rules"] = [
            {
                "id": str(r.id),
                "content": r.content,
                "category": r.category,
                "confidence": r.confidence,
                "status": r.status,
                "times_applied": r.times_applied,
            }
            for r in cluster.rules
        ]
        return data

    async def merge_cluster(self, cluster_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Merge all rules in a cluster into a single generalized rule using LLM.

        Archives the original rules and creates one merged rule.
        """
        result = await self.db.execute(
            select(RuleCluster)
            .options(selectinload(RuleCluster.rules))
            .where(RuleCluster.id == cluster_id)
        )
        cluster = result.scalar_one_or_none()
        if not cluster or not cluster.rules:
            return None

        rule_texts = [r.content for r in cluster.rules]

        # Use LLM to generate merged rule
        from app.core.llm import call_llm

        merge_prompt = (
            "You are a rule consolidation engine. Given the following similar user preference rules, "
            "create a single, clear, generalized rule that captures the intent of all of them. "
            "Return ONLY the merged rule text, nothing else.\n\n"
            "Rules to merge:\n"
            + "\n".join(f"- {t}" for t in rule_texts)
        )

        merged_content = await call_llm(
            messages=[{"role": "user", "content": merge_prompt}],
            temperature=0.3,
            max_tokens=256,
        )

        # Create merged rule
        max_confidence = max(r.confidence for r in cluster.rules)
        total_applied = sum(r.times_applied for r in cluster.rules)
        category = cluster.rules[0].category

        merged_rule = Rule(
            user_id=cluster.user_id,
            content=merged_content.strip(),
            original_correction=f"Merged from cluster '{cluster.name}' ({len(cluster.rules)} rules)",
            category=category,
            confidence=min(max_confidence + 0.1, 1.0),
            times_applied=total_applied,
            status="active",
        )
        self.db.add(merged_rule)

        # Archive original rules
        for rule in cluster.rules:
            rule.status = "archived"

        # Delete the cluster
        await self.db.execute(
            delete(rule_cluster_members).where(
                rule_cluster_members.c.cluster_id == cluster_id
            )
        )
        await self.db.execute(
            delete(RuleCluster).where(RuleCluster.id == cluster_id)
        )

        await self.db.flush()

        logger.info(
            "Cluster merged",
            extra={"extra_data": {
                "cluster_id": str(cluster_id),
                "rules_merged": len(rule_texts),
                "merged_rule_id": str(merged_rule.id),
            }},
        )

        return {
            "merged_rule_id": str(merged_rule.id),
            "merged_content": merged_rule.content,
            "rules_archived": len(rule_texts),
            "confidence": merged_rule.confidence,
        }
