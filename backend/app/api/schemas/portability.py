"""
Personal AI OS - Portability Schemas
"""
from pydantic import BaseModel, Field

class ExportRequest(BaseModel):
    encrypt: bool = Field(True, description="Whether to encrypt the exported payload")

class ExportResponse(BaseModel):
    payload: str = Field(..., description="The exported rules data")
    is_encrypted: bool

class ImportRequest(BaseModel):
    payload: str = Field(..., description="The exported rules data")
    is_encrypted: bool = Field(True, description="Whether the payload is encrypted")

class ImportResponse(BaseModel):
    status: str
    imported_count: int = 0
    message: str = ""
