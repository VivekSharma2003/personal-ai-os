"""
Personal AI OS - Cluster Schemas

Pydantic schemas for rule similarity clusters.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class ClusterRuleItem(BaseModel):
    """A rule within a cluster."""
    id: str
    content: str
    category: str
    confidence: float
    status: str
    times_applied: int


class ClusterResponse(BaseModel):
    """Single cluster summary."""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    rule_count: int
    avg_similarity: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ClusterDetailResponse(ClusterResponse):
    """Cluster with member rules."""
    rules: List[ClusterRuleItem] = []


class ClusterListResponse(BaseModel):
    """Paginated cluster list."""
    total: int
    limit: int
    offset: int
    clusters: List[ClusterResponse]


class GenerateClustersRequest(BaseModel):
    """Request to generate clusters."""
    similarity_threshold: Optional[float] = Field(
        default=None,
        ge=0.5,
        le=1.0,
        description="Minimum similarity to group rules (default from config)",
    )


class GenerateClustersResponse(BaseModel):
    """Result of cluster generation."""
    clusters_created: int
    total_rules_clustered: int
    clusters: List[ClusterResponse]


class MergeClusterResponse(BaseModel):
    """Result of merging a cluster."""
    merged_rule_id: str
    merged_content: str
    rules_archived: int
    confidence: float
