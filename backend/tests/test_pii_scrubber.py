"""
Personal AI OS - Test PII Scrubber
"""
import pytest
from app.services.pii_scrubber import PIIScrubberService

def test_pii_scrubber_service():
    service = PIIScrubberService(active=True)
    
    # Test Email
    text = "Contact me at john.doe@example.com for more info."
    scrubbed = service.scrub_text(text)
    assert "[EMAIL REDACTED]" in scrubbed
    assert "john.doe@example.com" not in scrubbed
    
    # Test SSN
    text = "My SSN is 123-45-6789 so please be careful."
    scrubbed = service.scrub_text(text)
    assert "[SSN REDACTED]" in scrubbed
    assert "123-45-6789" not in scrubbed
    
    # Test Credit Card
    text = "Use my card 4000 1234 5678 9010 to pay."
    scrubbed = service.scrub_text(text)
    assert "[CREDIT CARD REDACTED]" in scrubbed
    assert "4000 1234 5678 9010" not in scrubbed
    
    # Test Inactive
    service_inactive = PIIScrubberService(active=False)
    assert service_inactive.scrub_text(text) == text

@pytest.mark.asyncio
async def test_pii_api(client):
    response = await client.post(
        "/api/privacy/scrub",
        json={"text": "Here is my email: alice@wonderland.com"},
        headers={"X-User-ID": "api_privacy_user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "[EMAIL REDACTED]" in data["scrubbed_text"]
    assert "alice@wonderland.com" not in data["scrubbed_text"]
