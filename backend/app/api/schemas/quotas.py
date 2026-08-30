"""
Personal AI OS - Quota Schemas
"""
from pydantic import BaseModel
from typing import Optional

class QuotaMetric(BaseModel):
    used: int
    limit: int
    remaining: int

class QuotaStatusResponse(BaseModel):
    requests: QuotaMetric
    tokens: QuotaMetric
    allowed: bool
    reason: Optional[str] = None
