"""
Personal AI OS - Import Service

Bulk rule import with schema validation, dedup preview, and conflict-aware merging.
"""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule, RuleStatus
from app.core.llm import generate_embedding
from app.core.algorithms import cosine_similarity
from app.services.rule_engine import RuleEngineService


# Valid categories
VALID_CATEGORIES = {"style", "tone", "formatting", "logic", "safety"}

# Import strategies
STRATEGY_SKIP = "skip_duplicates"
STRATEGY_MERGE = "merge"
STRATEGY_OVERWRITE = "overwrite"


class ImportService:
    """Service for bulk rule import with deduplication and conflict handling."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_engine = RuleEngineService(db)

    def validate_import(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the schema of an import file.

        Expected format:
        {
            "rules": [
                {"content": "...", "category": "style", "original_correction": "..."},
                ...
            ]
        }

        Args:
            data: The parsed JSON data

        Returns:
            Dict with valid, errors, and validated_rules
        """
        errors = []
        validated_rules = []

        rules = data.get("rules")
        if not isinstance(rules, list):
            return {
                "valid": False,
                "errors": ["'rules' must be a list"],
                "validated_rules": [],
            }

        for i, rule in enumerate(rules):
            rule_errors = []

            if not isinstance(rule, dict):
                errors.append(f"Rule {i}: must be a dict")
                continue

            # Required field: content
            content = rule.get("content", "").strip()
            if not content:
                rule_errors.append(f"Rule {i}: 'content' is required and cannot be empty")

            # Category validation
            category = rule.get("category", "style").lower()
            if category not in VALID_CATEGORIES:
                rule_errors.append(
                    f"Rule {i}: category '{category}' is invalid. Must be one of: {', '.join(VALID_CATEGORIES)}"
                )

            if rule_errors:
                errors.extend(rule_errors)
            else:
                validated_rules.append({
                    "content": content,
                    "category": category,
                    "original_correction": rule.get("original_correction", "Imported rule"),
                    "confidence": min(max(float(rule.get("confidence", 0.5)), 0.1), 0.95),
                })

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "validated_rules": validated_rules,
        }

    async def preview_import(
        self,
        user_id: UUID,
        rules: List[dict],
        similarity_threshold: float = 0.85
    ) -> Dict[str, Any]:
        """
        Dry-run an import, showing what would happen without making changes.

        Args:
            user_id: UUID of the user
            rules: List of validated rule dicts
            similarity_threshold: Threshold for duplicate detection

        Returns:
            Dict with to_create, to_merge, to_skip lists
        """
        # Get existing rules and their embeddings
        existing_rules = await self.rule_engine.get_active_rules(user_id)
        existing_data = [r.to_dict() for r in existing_rules]

        # Pre-compute embeddings for existing rules
        existing_embeddings = {}
        for rule in existing_rules:
            try:
                existing_embeddings[str(rule.id)] = await generate_embedding(rule.content)
            except Exception:
                pass

        to_create = []
        to_merge = []
        to_skip = []

        for import_rule in rules:
            try:
                import_embedding = await generate_embedding(import_rule["content"])
            except Exception:
                # Can't check for duplicates without embedding
                to_create.append(import_rule)
                continue

            # Check against existing rules
            best_match = None
            best_similarity = 0.0

            for existing in existing_data:
                existing_emb = existing_embeddings.get(existing["id"])
                if existing_emb is None:
                    continue

                similarity = cosine_similarity(import_embedding, existing_emb)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = existing

            if best_similarity >= similarity_threshold:
                to_merge.append({
                    "import_rule": import_rule,
                    "existing_rule": best_match,
                    "similarity": round(best_similarity, 3),
                })
            elif best_similarity >= 0.7:
                to_skip.append({
                    "import_rule": import_rule,
                    "similar_rule": best_match,
                    "similarity": round(best_similarity, 3),
                    "reason": "Potentially similar to existing rule",
                })
            else:
                to_create.append(import_rule)

        return {
            "to_create": to_create,
            "to_merge": to_merge,
            "to_skip": to_skip,
            "summary": {
                "total_input": len(rules),
                "will_create": len(to_create),
                "will_merge": len(to_merge),
                "will_skip": len(to_skip),
            }
        }

    async def execute_import(
        self,
        user_id: UUID,
        rules: List[dict],
        strategy: str = STRATEGY_SKIP,
        similarity_threshold: float = 0.85
    ) -> Dict[str, Any]:
        """
        Execute a bulk rule import.

        Args:
            user_id: UUID of the user
            rules: List of validated rule dicts
            strategy: Import strategy (skip_duplicates, merge, overwrite)
            similarity_threshold: Threshold for duplicate detection

        Returns:
            Dict with results: created, merged, skipped counts and details
        """
        preview = await self.preview_import(user_id, rules, similarity_threshold)

        created = []
        merged = []
        skipped = []

        # Create new rules
        for rule_data in preview["to_create"]:
            try:
                embedding = await generate_embedding(rule_data["content"])
            except Exception:
                embedding = None

            rule = await self.rule_engine.create_rule(
                user_id=user_id,
                content=rule_data["content"],
                category=rule_data["category"],
                original_correction=rule_data.get("original_correction", "Imported rule"),
                embedding=embedding,
            )
            created.append(rule.to_dict())

        # Handle duplicates based on strategy
        for match in preview["to_merge"]:
            if strategy == STRATEGY_SKIP:
                skipped.append({
                    "content": match["import_rule"]["content"],
                    "reason": f"Duplicate of existing rule (similarity: {match['similarity']})",
                })
            elif strategy == STRATEGY_MERGE:
                # Reinforce the existing rule
                existing_id = UUID(match["existing_rule"]["id"])
                await self.rule_engine.reinforce_rule(existing_id)
                merged.append({
                    "existing_rule_id": match["existing_rule"]["id"],
                    "import_content": match["import_rule"]["content"],
                    "similarity": match["similarity"],
                })
            elif strategy == STRATEGY_OVERWRITE:
                # Update the existing rule's content
                existing_id = UUID(match["existing_rule"]["id"])
                await self.rule_engine.update_rule(
                    existing_id,
                    content=match["import_rule"]["content"]
                )
                merged.append({
                    "existing_rule_id": match["existing_rule"]["id"],
                    "old_content": match["existing_rule"]["content"],
                    "new_content": match["import_rule"]["content"],
                })

        # Handle near-matches
        for near in preview["to_skip"]:
            if strategy == STRATEGY_OVERWRITE:
                # Force create even if similar
                try:
                    embedding = await generate_embedding(near["import_rule"]["content"])
                except Exception:
                    embedding = None

                rule = await self.rule_engine.create_rule(
                    user_id=user_id,
                    content=near["import_rule"]["content"],
                    category=near["import_rule"]["category"],
                    original_correction=near["import_rule"].get("original_correction", "Imported rule"),
                    embedding=embedding,
                )
                created.append(rule.to_dict())
            else:
                skipped.append({
                    "content": near["import_rule"]["content"],
                    "reason": near["reason"],
                })

        return {
            "created": created,
            "merged": merged,
            "skipped": skipped,
            "summary": {
                "total_input": len(rules),
                "created": len(created),
                "merged": len(merged),
                "skipped": len(skipped),
            }
        }


def get_available_templates() -> List[Dict[str, Any]]:
    """
    List available pre-built rule template packs.

    Returns:
        List of template metadata dicts
    """
    import os
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "templates")

    templates = []
    if os.path.exists(templates_dir):
        for filename in sorted(os.listdir(templates_dir)):
            if filename.endswith(".json"):
                filepath = os.path.join(templates_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                    templates.append({
                        "id": filename.replace(".json", ""),
                        "name": data.get("name", filename),
                        "description": data.get("description", ""),
                        "rule_count": len(data.get("rules", [])),
                        "categories": list(set(r.get("category", "style") for r in data.get("rules", []))),
                    })
                except Exception:
                    pass

    return templates


def load_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Load a template by ID."""
    import os
    filepath = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "templates", f"{template_id}.json"
    )
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return None
