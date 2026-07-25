"""
Personal AI OS - Simulation Schemas

Pydantic schemas for rule impact simulation (dry-run).
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class SimulateRuleRequest(BaseModel):
    """Request to simulate adding a new rule."""
    draft_rule_content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The rule content to simulate",
    )
    test_prompts: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Prompts to test the rule against (max 5)",
    )


class SimulateEditRequest(BaseModel):
    """Request to simulate editing an existing rule."""
    rule_id: str
    new_content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="New rule content to simulate",
    )
    test_prompts: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Prompts to test the edit against (max 5)",
    )


class SimulationResultItem(BaseModel):
    """Result for a single test prompt."""
    prompt: str
    response_without: str
    response_with: str
    diff_summary: str
    impact_score: float


class SimulateRuleResponse(BaseModel):
    """Full simulation result for a new rule."""
    simulation_type: str
    draft_rule: str
    prompts_tested: int
    avg_impact_score: float
    results: List[SimulationResultItem]


class SimulateEditResponse(BaseModel):
    """Full simulation result for editing a rule."""
    simulation_type: str
    rule_id: str
    old_content: str
    new_content: str
    prompts_tested: int
    avg_impact_score: float
    results: List[SimulationResultItem]
