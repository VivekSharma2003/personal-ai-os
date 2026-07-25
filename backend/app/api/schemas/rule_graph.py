"""
Personal AI OS - Rule Graph Schemas

Pydantic schemas for rule execution graph endpoints.
"""
from pydantic import BaseModel
from typing import List, Dict, Optional


class RuleNode(BaseModel):
    """Schema for a rule node inside a topology list."""
    id: str
    content: str


class RuleGraphTopologyResponse(BaseModel):
    """Response schema for rule execution graph topology."""
    has_cycle: bool
    cycle_nodes: List[str]
    topological_order: List[RuleNode]
    adjacency_list: Dict[str, List[str]]


class CycleDetectionResponse(BaseModel):
    """Response schema for cycle detection endpoint."""
    has_cycle: bool
    cycle_nodes: List[str]


class ConflictPathResponse(BaseModel):
    """Response schema for conflict path analysis result."""
    type: str
    description: str
    rule_id: str
    conflicting_rule_id: Optional[str] = None
    required_rules: Optional[List[str]] = None
