"""
Personal AI OS - A/B Testing Schemas
"""
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


class VariantInput(BaseModel):
    label: str
    prompt_template: str


class CreateExperimentRequest(BaseModel):
    name: str
    variants: List[VariantInput]


class RecordResultRequest(BaseModel):
    variant_id: UUID
    score: float
    feedback: Optional[str] = None


class VariantStats(BaseModel):
    variant_id: str
    label: str
    responses: int
    avg_score: Optional[float]
