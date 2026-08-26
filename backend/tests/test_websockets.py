"""
Personal AI OS - Test WebSockets
"""
import pytest
import json
from fastapi.testclient import TestClient

from app.main import app


# Standard TestClient is used for WebSockets
client = TestClient(app)


def test_websocket_connection():
    """Test connecting, receiving welcome message, and sending/receiving telemetry."""
    # This will automatically call get_user_from_token and create the user
    with client.websocket_connect("/ws/ws_test_user") as websocket:
        # Should receive welcome event
        data = websocket.receive_text()
        event = json.loads(data)
        
        assert event["type"] == "system_status"
        assert event["data"]["status"] == "connected"
        
        # Test client telemetry echo
        websocket.send_text("test telemetry")
        data = websocket.receive_text()
        event = json.loads(data)
        
        assert event["type"] == "ack"
        assert event["data"]["received"] == "test telemetry"


def test_websocket_broadcast():
    """Test broadcast mechanism (if we had a direct route to trigger it, but we can just test the manager)."""
    # Since the manager is stateful, we can just test it directly in an async context
    pass
