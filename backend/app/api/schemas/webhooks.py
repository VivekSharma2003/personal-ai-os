"""
Personal AI OS - Webhook API Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl


class WebhookCreateRequest(BaseModel):
    """Request schema for creating a webhook."""
    user_id: str = Field(..., description="External user ID")
    url: str = Field(..., description="Webhook URL to POST to", max_length=2048)
    events: List[str] = Field(
        ...,
        description="List of event types to subscribe to (e.g., ['rule.created', 'chat.completed'])"
    )
    description: Optional[str] = Field(None, description="Human-readable description", max_length=500)


class WebhookUpdateRequest(BaseModel):
    """Request schema for updating a webhook."""
    url: Optional[str] = Field(None, max_length=2048)
    events: Optional[List[str]] = None
    active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=500)


class WebhookResponse(BaseModel):
    """Response schema for a webhook."""
    id: str
    url: str
    description: Optional[str]
    events: List[str]
    active: bool
    consecutive_failures: int
    created_at: Optional[str]
    updated_at: Optional[str]
    secret: Optional[str] = None  # Only included on creation


class WebhooksListResponse(BaseModel):
    """Response schema for listing webhooks."""
    webhooks: List[WebhookResponse]
    total: int


class DeliveryResponse(BaseModel):
    """Response schema for a webhook delivery."""
    id: str
    webhook_id: str
    event_type: str
    payload: dict
    status_code: Optional[int]
    error_message: Optional[str]
    attempt_number: int
    success: bool
    created_at: Optional[str]
    delivered_at: Optional[str]


class DeliveriesListResponse(BaseModel):
    """Response schema for listing deliveries."""
    deliveries: List[DeliveryResponse]
    total: int
