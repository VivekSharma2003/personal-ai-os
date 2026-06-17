"""
Tests for Rule Dependency Chains.
"""
import pytest
import pytest_asyncio
from uuid import uuid4

from app.models.rule import Rule, RuleStatus
from app.models.user import User
from app.services.dependency_service import DependencyService
from app.models.rule_dependency import DependencyType


@pytest_asyncio.fixture
async def dep_rules(db_session):
    """Create a user with 3 rules for dependency testing."""
    user = User(external_id=f"dep_test_{uuid4().hex[:8]}")
    db_session.add(user)
    await db_session.flush()

    rule_formal = Rule(
        user_id=user.id,
        content="Use formal tone in all communications",
        category="tone",
        confidence=0.8,
        status=RuleStatus.ACTIVE.value,
    )
    rule_bullets = Rule(
        user_id=user.id,
        content="Use bullet points for lists",
        category="formatting",
        confidence=0.7,
        status=RuleStatus.ACTIVE.value,
    )
    rule_casual = Rule(
        user_id=user.id,
        content="Use casual greetings like 'hey'",
        category="tone",
        confidence=0.6,
        status=RuleStatus.ACTIVE.value,
    )

    db_session.add_all([rule_formal, rule_bullets, rule_casual])
    await db_session.flush()

    return user, rule_formal, rule_bullets, rule_casual


@pytest.mark.asyncio
async def test_add_requires_dependency(db_session, dep_rules):
    """Test creating a 'requires' dependency."""
    _, rule_formal, rule_bullets, _ = dep_rules
    service = DependencyService(db_session)

    dep = await service.add_dependency(
        rule_id=rule_bullets.id,
        depends_on_rule_id=rule_formal.id,
        dependency_type=DependencyType.REQUIRES.value,
    )

    assert dep is not None
    assert dep.dependency_type == DependencyType.REQUIRES.value


@pytest.mark.asyncio
async def test_self_dependency_raises(db_session, dep_rules):
    """Test that a rule cannot depend on itself."""
    _, rule_formal, _, _ = dep_rules
    service = DependencyService(db_session)

    with pytest.raises(ValueError, match="cannot depend on itself"):
        await service.add_dependency(
            rule_id=rule_formal.id,
            depends_on_rule_id=rule_formal.id,
        )


@pytest.mark.asyncio
async def test_resolve_requires_satisfied(db_session, dep_rules):
    """Test that requires dependencies pass when parent is active."""
    _, rule_formal, rule_bullets, _ = dep_rules
    service = DependencyService(db_session)

    await service.add_dependency(
        rule_id=rule_bullets.id,
        depends_on_rule_id=rule_formal.id,
        dependency_type=DependencyType.REQUIRES.value,
    )

    # Both rules active — bullets should be included
    resolved = await service.resolve_chain([rule_formal.id, rule_bullets.id])
    assert rule_bullets.id in resolved
    assert rule_formal.id in resolved


@pytest.mark.asyncio
async def test_resolve_requires_not_satisfied(db_session, dep_rules):
    """Test that requires dependencies fail when parent is missing."""
    _, rule_formal, rule_bullets, _ = dep_rules
    service = DependencyService(db_session)

    await service.add_dependency(
        rule_id=rule_bullets.id,
        depends_on_rule_id=rule_formal.id,
        dependency_type=DependencyType.REQUIRES.value,
    )

    # Only bullets active (formal not in list) — bullets should be excluded
    resolved = await service.resolve_chain([rule_bullets.id])
    assert rule_bullets.id not in resolved


@pytest.mark.asyncio
async def test_resolve_excludes(db_session, dep_rules):
    """Test that excludes dependencies filter correctly."""
    _, rule_formal, _, rule_casual = dep_rules
    service = DependencyService(db_session)

    # Casual EXCLUDES formal (can't be casual if formal is active)
    await service.add_dependency(
        rule_id=rule_casual.id,
        depends_on_rule_id=rule_formal.id,
        dependency_type=DependencyType.EXCLUDES.value,
    )

    # Both active — casual should be excluded
    resolved = await service.resolve_chain([rule_formal.id, rule_casual.id])
    assert rule_formal.id in resolved
    assert rule_casual.id not in resolved

    # Only casual — should be included
    resolved = await service.resolve_chain([rule_casual.id])
    assert rule_casual.id in resolved


@pytest.mark.asyncio
async def test_cycle_detection(db_session, dep_rules):
    """Test that circular dependencies are detected."""
    _, rule_formal, rule_bullets, _ = dep_rules
    service = DependencyService(db_session)

    # formal → bullets
    await service.add_dependency(
        rule_id=rule_formal.id,
        depends_on_rule_id=rule_bullets.id,
    )

    # bullets → formal would create a cycle
    with pytest.raises(ValueError, match="circular"):
        await service.add_dependency(
            rule_id=rule_bullets.id,
            depends_on_rule_id=rule_formal.id,
        )


@pytest.mark.asyncio
async def test_dependency_graph(db_session, dep_rules):
    """Test the dependency graph endpoint."""
    user, rule_formal, rule_bullets, _ = dep_rules
    service = DependencyService(db_session)

    await service.add_dependency(
        rule_id=rule_bullets.id,
        depends_on_rule_id=rule_formal.id,
    )

    graph = await service.get_dependency_graph(user.id)
    assert graph["total_rules"] == 3
    assert graph["rules_with_dependencies"] == 2
    assert len(graph["edges"]) == 1
