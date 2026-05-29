import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from app.models.user import User
from app.models.rule import Rule
from app.services.import_service import ImportService

@pytest.mark.asyncio
async def test_validate_import():
    # We don't need a DB session for a simple pure validation function
    service = ImportService(None)

    # Valid schema
    valid_data = {
        "rules": [
            {"content": "Format output in markdown", "category": "formatting"},
            {"content": "Never use contractions", "category": "style", "confidence": 0.8}
        ]
    }
    res = service.validate_import(valid_data)
    assert res["valid"] is True
    assert len(res["validated_rules"]) == 2
    assert res["validated_rules"][0]["category"] == "formatting"

    # Invalid schemas
    invalid_data = {
        "rules": [
            {"content": "", "category": "invalid_cat"}
        ]
    }
    res_invalid = service.validate_import(invalid_data)
    assert res_invalid["valid"] is False
    assert len(res_invalid["errors"]) > 0

@pytest.mark.asyncio
@patch("app.services.import_service.generate_embedding")
@patch("app.services.import_service.cosine_similarity")
async def test_preview_and_execute_import(mock_similarity, mock_emb, db_session):
    user = User(external_id="import_user")
    db_session.add(user)
    await db_session.flush()

    service = ImportService(db_session)

    # Pre-populate one existing rule
    existing_rule = Rule(
        user_id=user.id,
        content="Use formal tone always",
        category="style",
        confidence=0.5
    )
    db_session.add(existing_rule)
    await db_session.flush()

    # Mock embeddings & similarities:
    # Match rule 1 (highly similar, similarity = 0.9)
    # Create rule 2 (dissimilar, similarity = 0.2)
    # Since preview is run twice (directly and inside execute_import), we need 4 values.
    mock_emb.return_value = [0.1] * 1536
    mock_similarity.side_effect = [0.9, 0.2, 0.9, 0.2]

    import_rules = [
        {"content": "Always use a formal tone", "category": "style"},
        {"content": "Be concise with code", "category": "formatting"}
    ]

    # Test preview
    preview = await service.preview_import(user.id, import_rules)
    assert preview["summary"]["will_create"] == 1
    assert preview["summary"]["will_merge"] == 1

    # Test execution with 'merge' strategy
    result = await service.execute_import(user.id, import_rules, strategy="merge")
    await db_session.flush()

    assert result["summary"]["created"] == 1
    assert result["summary"]["merged"] == 1
    
    # Check that the existing rule was reinforced (confidence increased)
    reloaded_existing = await db_session.get(Rule, existing_rule.id)
    assert reloaded_existing.times_reinforced == 1
    assert reloaded_existing.confidence > 0.5
