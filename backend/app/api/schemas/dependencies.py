"""
Personal AI OS - Rule Dependency Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class DependencyCreateRequest(BaseModel):
    """Request to create a dependency between two rules."""
    depends_on_rule_id: str = Field(..., description="UUID of the parent rule")
    dependency_type: str = Field(
        default="requires",
        description="Type: 'requires', 'excludes', or 'enhances'",
    )


class DependencyResponse(BaseModel):
    """Response for a single dependency."""
    id: str
    rule_id: str
    depends_on_rule_id: str
    dependency_type: str
    depends_on_content: Optional[str] = None
    rule_content: Optional[str] = None
    created_at: Optional[str] = None


class DependencyListResponse(BaseModel):
    """List of dependencies for a rule."""
    dependencies: List[DependencyResponse]
    total: int


class GraphNode(BaseModel):
    """A node in the dependency graph."""
    id: str
    content: str
    category: str
    status: str


class GraphEdge(BaseModel):
    """An edge in the dependency graph."""
    source: str = Field(alias="from")
    target: str = Field(alias="to")
    type: str

    class Config:
        populate_by_name = True


class DependencyGraphResponse(BaseModel):
    """Full dependency graph for visualization."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_rules: int
    rules_with_dependencies: int
