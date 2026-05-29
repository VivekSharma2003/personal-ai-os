# pyrefly: ignore [missing-import]
import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from app.models.user import User
from app.models.rule import Rule
from app.core.conflict_detector import detect_pairwise_conflict, prefilter_potential_conflicts, scan_all_conflicts
from app.services.conflicts import ConflictService

@pytest.mark.asyncio
@patch("app.core.conflict_detector.generate_embedding")
async def test_prefilter_potential_conflicts(mock_emb):
    # Mock embeddings to calculate cosine similarity
    # Let's say rule A and rule B are highly similar, while rule C is different
    mock_emb.side_effect = lambda text: {
        "Rule A": [1.0, 0.0, 0.0],
        "Rule B": [0.9, 0.1, 0.0],
        "Rule C": [0.0, 0.0, 1.0],
    }.get(text, [0.0, 0.0, 0.0])

    target = {"id": "1", "content": "Rule A"}
    candidates = [
        {"id": "2", "content": "Rule B"},
        {"id": "3", "content": "Rule C"},
    ]

    filtered = await prefilter_potential_conflicts(target, candidates, similarity_threshold=0.5)
    assert len(filtered) == 1
    assert filtered[0]["content"] == "Rule B"

@pytest.mark.asyncio
@patch("app.core.conflict_detector.extract_json_response")
async def test_detect_pairwise_conflict(mock_extract):
    # Mock LLM conflict response
    mock_extract.return_value = {
        "conflicts": True,
        "severity": 0.8,
        "explanation": "Contradictory instructions on tone",
        "suggested_resolution": "merge",
        "merged_rule": "Use neutral tone"
    }

    res = await detect_pairwise_conflict("use formal tone", "use informal tone")
    assert res["conflicts"] is True
    assert res["severity"] == 0.8
    assert res["suggested_resolution"] == "merge"
    assert res["merged_rule"] == "Use neutral tone"

@pytest.mark.asyncio
@patch("app.core.conflict_detector.generate_embedding")
@patch("app.core.conflict_detector.detect_pairwise_conflict")
async def test_scan_all_conflicts(mock_detect, mock_emb):
    mock_emb.return_value = [0.1, 0.2, 0.3]
    mock_detect.return_value = {
        "conflicts": True,
        "severity": 0.9,
        "explanation": "Direct contradiction",
        "suggested_resolution": "disable_one",
        "merged_rule": None
    }

    rules = [
        {"id": "r1", "content": "Tone is formal"},
        {"id": "r2", "content": "Tone is casual"}
    ]

    conflicts = await scan_all_conflicts(rules, similarity_threshold=0.0)
    assert len(conflicts) == 1
    assert conflicts[0]["rule_a_id"] == "r1"
    assert conflicts[0]["rule_b_id"] == "r2"
    assert conflicts[0]["severity"] == 0.9
