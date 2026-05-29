import pytest
import json
import hmac
import hashlib
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from app.models.user import User
from app.models.webhook import Webhook, WebhookDelivery
from app.services.webhook_service import WebhookService

@pytest.mark.asyncio
async def test_webhook_crud(db_session):
    user = User(external_id="webhook_crud_user")
    db_session.add(user)
    await db_session.flush()

    service = WebhookService(db_session)

    # 1. Create a webhook
    webhook = await service.create_webhook(
        user_id=user.id,
        url="https://example.com/webhook",
        events=["rule.created", "chat.completed"],
        description="My test webhook"
    )
    await db_session.flush()

    assert webhook.id is not None
    assert webhook.url == "https://example.com/webhook"
    assert webhook.active is True
    assert webhook.secret is not None

    # 2. Get webhooks
    webhooks = await service.get_webhooks(user.id)
    assert len(webhooks) == 1
    assert webhooks[0].id == webhook.id

    # 3. Update webhook
    updated = await service.update_webhook(webhook.id, url="https://example.com/new-url")
    await db_session.flush()
    assert updated.url == "https://example.com/new-url"

    # 4. Delete webhook
    deleted = await service.delete_webhook(webhook.id)
    await db_session.flush()
    assert deleted is True

    webhooks = await service.get_webhooks(user.id)
    assert len(webhooks) == 0

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_webhook_delivery_and_signature(mock_post, db_session):
    user = User(external_id="webhook_delivery_user")
    db_session.add(user)
    await db_session.flush()

    service = WebhookService(db_session)

    webhook = await service.create_webhook(
        user_id=user.id,
        url="https://example.com/webhook",
        events=["rule.created"],
        description="Delivery test"
    )
    await db_session.flush()

    # Mock success HTTP response
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = "OK"
    mock_post.return_value = mock_resp

    payload = {"rule_id": str(uuid4()), "content": "Keep it casual"}
    
    deliveries = await service.deliver_event(
        event_type="rule.created",
        payload=payload,
        user_id=user.id
    )
    await db_session.flush()

    assert len(deliveries) == 1
    assert deliveries[0].success is True
    assert deliveries[0].status_code == 200

    # Verify signature in post call
    assert mock_post.called
    kwargs = mock_post.call_args.kwargs
    headers = kwargs["headers"]
    body = kwargs["content"]

    assert "X-Webhook-Signature" in headers
    signature_header = headers["X-Webhook-Signature"]
    assert signature_header.startswith("sha256=")
    sent_sig = signature_header.split("sha256=")[1]

    # Validate signature calculation
    expected_sig = hmac.new(
        webhook.secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    assert sent_sig == expected_sig

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_webhook_retry_failed_deliveries(mock_post, db_session):
    user = User(external_id="webhook_retry_user")
    db_session.add(user)
    await db_session.flush()

    service = WebhookService(db_session)

    webhook = await service.create_webhook(
        user_id=user.id,
        url="https://example.com/webhook",
        events=["rule.created"]
    )
    await db_session.flush()

    # 1. Simulate a failed delivery attempt (HTTP 500)
    mock_resp = AsyncMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_post.return_value = mock_resp

    deliveries = await service.deliver_event(
        event_type="rule.created",
        payload={"data": "test"},
        user_id=user.id
    )
    await db_session.flush()

    assert len(deliveries) == 1
    assert deliveries[0].success is False
    assert deliveries[0].attempt_number == 1

    # 2. Mock a successful retry (HTTP 200)
    mock_resp_success = AsyncMock()
    mock_resp_success.status_code = 200
    mock_resp_success.text = "Success"
    mock_post.return_value = mock_resp_success

    retried_count = await service.retry_failed_deliveries()
    await db_session.flush()

    assert retried_count == 1
    # Check that the delivery object has been updated
    delivery = await db_session.get(WebhookDelivery, deliveries[0].id)
    assert delivery.success is True
    assert delivery.attempt_number == 2
