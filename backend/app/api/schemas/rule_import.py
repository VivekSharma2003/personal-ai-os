"""
Personal AI OS - Rule Import API Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ImportRuleItem(BaseModel):
    """A single rule in an import payload."""
    content: str = Field(..., description="Rule content text")
    category: str = Field(default="style", description="Category: style, tone, formatting, logic, safety")
    original_correction: Optional[str] = Field(None, description="Original correction text")
    confidence: Optional[float] = Field(0.5, ge=0.1, le=0.95, description="Initial confidence")


class ImportPreviewRequest(BaseModel):
    """Request schema for previewing an import."""
    user_id: str = Field(..., description="External user ID")
    rules: List[ImportRuleItem] = Field(..., description="Rules to import")


class ImportExecuteRequest(BaseModel):
    """Request schema for executing an import."""
    user_id: str = Field(..., description="External user ID")
    rules: List[ImportRuleItem] = Field(..., description="Rules to import")
    strategy: str = Field(
        default="skip_duplicates",
        description="Import strategy: skip_duplicates, merge, overwrite"
    )


class ImportPreviewResponse(BaseModel):
    """Response schema for an import preview."""
    to_create: List[dict]
    to_merge: List[dict]
    to_skip: List[dict]
    summary: dict


class ImportExecuteResponse(BaseModel):
    """Response schema for an executed import."""
    created: List[dict]
    merged: List[dict]
    skipped: List[dict]
    summary: dict


class TemplateResponse(BaseModel):
    """Response schema for a rule template pack."""
    id: str
    name: str
    description: str
    rule_count: int
    categories: List[str]


class TemplatesListResponse(BaseModel):
    """Response schema for listing templates."""
    templates: List[TemplateResponse]
    total: int
