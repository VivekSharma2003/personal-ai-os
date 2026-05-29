import pytest
from uuid import uuid4
from app.models.user import User
from app.models.rule import Rule, RuleStatus, RuleCategory
from app.services.versioning import VersioningService
from app.services.rule_engine import RuleEngineService

@pytest.mark.asyncio
async def test_versioning_flow(db_session):
    # 1. Create a user
    user = User(external_id="versioning_test_user")
    db_session.add(user)
    await db_session.flush()

    # 2. Initialize services
    rule_engine = RuleEngineService(db_session)
    versioning = VersioningService(db_session)

    # 3. Create a rule
    rule = await rule_engine.create_rule(
        user_id=user.id,
        content="Default formal tone",
        category="style",
        original_correction="Use formal tone please"
    )
    await db_session.flush()

    # 4. Update rule (this should trigger version snapshot before update)
    updated_rule = await rule_engine.update_rule(
        rule_id=rule.id,
        content="Strict formal tone, no contractions",
        category="style"
    )
    await db_session.flush()

    # 5. Check history - there should be 1 version (representing the initial state)
    history = await versioning.get_history(rule.id)
    assert len(history) == 1
    assert history[0].version_number == 1
    assert history[0].content == "Default formal tone"
    assert history[0].category == "style"

    # 6. Update the rule again
    await rule_engine.update_rule(
        rule_id=rule.id,
        status="disabled"
    )
    await db_session.flush()

    # History should now have 2 versions
    history = await versioning.get_history(rule.id)
    assert len(history) == 2
    assert history[0].version_number == 2  # Newest version is first
    assert history[0].content == "Strict formal tone, no contractions"
    assert history[0].status == "active"

    # 7. Test rollback to version 1
    rolled_back = await versioning.rollback(rule.id, 1)
    await db_session.flush()
    assert rolled_back.content == "Default formal tone"
    assert rolled_back.status == "active"

    # 8. Test diff
    diff_result = await versioning.diff(rule.id, 1, 2)
    assert diff_result["has_changes"] is True
    assert len(diff_result["changes"]) > 0
