"""
Personal AI OS - Webhook API Routes
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.webhooks import (
    WebhookCreateRequest, WebhookUpdateRequest,
    WebhookResponse, WebhooksListResponse,
    DeliveryResponse, DeliveriesListResponse
)
from app.dependencies import get_db
from app.services.webhook_service import WebhookService
from app.services.rule_engine import RuleEngineService


router = APIRouter()


@router.post("/webhooks", response_model=WebhookResponse)
async def create_webhook(
    request: WebhookCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new webhook for receiving event notifications."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(request.user_id)

    webhook_service = WebhookService(db)
    webhook = await webhook_service.create_webhook(
        user_id=user.id,
        url=request.url,
        events=request.events,
        description=request.description,
    )

    await db.commit()

    # Include secret only on creation
    return WebhookResponse(**webhook.to_dict(include_secret=True))


@router.get("/webhooks", response_model=WebhooksListResponse)
async def list_webhooks(
    user_id: str = Query(..., description="External user ID"),
    db: AsyncSession = Depends(get_db)
):
    """List all webhooks for a user."""
    rule_engine = RuleEngineService(db)
    user = await rule_engine.get_or_create_user(user_id)

    webhook_service = WebhookService(db)
    webhooks = await webhook_service.get_webhooks(user.id)

    return WebhooksListResponse(
        webhooks=[WebhookResponse(**w.to_dict()) for w in webhooks],
        total=len(webhooks),
    )


@router.patch("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a webhook's configuration."""
    webhook_service = WebhookService(db)
    webhook = await webhook_service.update_webhook(
        webhook_id=UUID(webhook_id),
        url=request.url,
        events=request.events,
        active=request.active,
        description=request.description,
    )

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await db.commit()
    return WebhookResponse(**webhook.to_dict())


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a webhook and its delivery history."""
    webhook_service = WebhookService(db)
    deleted = await webhook_service.delete_webhook(UUID(webhook_id))

    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await db.commit()
    return {"status": "deleted", "webhook_id": webhook_id}


@router.get("/webhooks/{webhook_id}/deliveries", response_model=DeliveriesListResponse)
async def list_deliveries(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """View delivery history for a webhook."""
    webhook_service = WebhookService(db)

    webhook = await webhook_service.get_webhook(UUID(webhook_id))
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    deliveries = await webhook_service.get_deliveries(UUID(webhook_id), limit=limit)

    return DeliveriesListResponse(
        deliveries=[DeliveryResponse(**d.to_dict()) for d in deliveries],
        total=len(deliveries),
    )


@router.post("/webhooks/{webhook_id}/test", response_model=DeliveryResponse)
async def test_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Send a test event to a webhook."""
    webhook_service = WebhookService(db)

    delivery = await webhook_service.send_test_event(UUID(webhook_id))
    if not delivery:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await db.commit()
    return DeliveryResponse(**delivery.to_dict())
