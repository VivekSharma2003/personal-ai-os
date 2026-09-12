"""
Personal AI OS - Rule Compression Schemas
"""
from pydantic import BaseModel
from typing import Optional

class CompressionRequest(BaseModel):
    category: str

class CompressionResponse(BaseModel):
    status: str
    message: Optional[str] = None
    compressed_count: Optional[int] = None
    new_rule_id: Optional[str] = None
