"""
Integration Tests for Ontology Expert Collaboration WebSocket API

Tests the WebSocket handlers for real-time collaboration including:
- Connection and disconnection
- Message broadcasting
- Element locking/unlocking
- Concurrent connections
- Error handling

Requirements: Task 16.5 - Write integration tests for WebSocket
"""

import asyncio
import json
import pytest
from datetime import datetime
from typing import Dict, Any, List
from uuid import uuid4

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

# Import the FastAPI app
from src.app import app
from src.api.ontology_collaboration_websocket import (
    MessageType,
    WebSocketMessage,
    ConnectionManager,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid4())


@pytest.fixture
def expert_id() -> str:
    """Generate a unique expert ID."""
    return str(uuid4())


@pytest.fixture
def connection_manager():
    """Create a fresh connection manager for testing."""
    return ConnectionManager()


# =============================================================================
# Connection Tests
# =============================================================================

class TestWebSocketConnection:
    """Tests for WebSocket connection handling."""
    
    def test_websocket_connect(self, client, session_id, expert_id):
        """Test WebSocket connection establishment."""
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert_id}"
        ) as websocket:
            # Should receive initial presence update
            data = websocket.receive_text()
            message = json.loads(data)
            
            assert message["type"] == MessageType.PRESENCE_UPDATE.value
            assert "participants" in message.get("data", {})
    
    def test_websocket_disconnect(self, client, session_id, expert_id):
        """Test WebSocket disconnection handling."""
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert_id}"
        ) as websocket:
            # Receive initial message
            websocket.receive_text()
            
            # Close connection
            websocket.close()
        
        # Connection should be cleaned up
        # Verify via REST endpoint
        response = client.get(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/participants"
        )
        assert response.status_code == 200
        data = response.json()
        assert expert_id not in data.get("participants", [])
    
    def test_websocket_missing_expert_id(self, client, session_id):
        """Test WebSocket connection without expert_id."""
        # Should fail without expert_id
        with pytest.raises(Exception):
            with client.websocket_connect(
                f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws"
            ) as websocket:
                pass


# =============================================================================
# Message Broadcasting Tests
# =============================================================================

class TestMessageBroadcasting:
    """Tests for WebSocket message broadcasting."""
    
    def test_participant_joined_broadcast(self, client, session_id):
        """Test that participant joined is broadcast to other participants."""
        expert1_id = str(uuid4())
        expert2_id = str(uuid4())
        
        # First expert connects
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert1_id}"
        ) as ws1:
            # Receive initial presence
            ws1.receive_text()
            
            # Second expert connects
            with client.websocket_connect(
                f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert2_id}"
            ) as ws2:
                # First expert should receive participant joined
                data = ws1.receive_text()
                message = json.loads(data)
                
                assert message["type"] == MessageType.PARTICIPANT_JOINED.value
                assert message["expert_id"] == expert2_id
    
    def test_element_update_broadcast(self, client, session_id, expert_id):
        """Test that element updates are broadcast to session."""
        expert1_id = str(uuid4())
        expert2_id = str(uuid4())
        element_id = str(uuid4())
        
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert1_id}"
        ) as ws1:
            ws1.receive_text()  # Initial presence
            
            with client.websocket_connect(
                f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert2_id}"
            ) as ws2:
                ws2.receive_text()  # Initial presence
                ws1.receive_text()  # Participant joined
                
                # Expert 2 sends edit
                ws2.send_text(json.dumps({
                    "type": MessageType.EDIT_ELEMENT.value,
                    "element_id": element_id,
                    "data": {"changes": {"name": "新名称"}}
                }))
                
                # Expert 1 should receive update
                data = ws1.receive_text()
                message = json.loads(data)
                
                assert message["type"] == MessageType.ELEMENT_UPDATED.value
                assert message["element_id"] == element_id


# =============================================================================
# Element Locking Tests
# =============================================================================

class TestElementLocking:
    """Tests for element locking functionality."""
    
    def test_lock_element_success(self, client, session_id, expert_id):
        """Test successful element locking."""
        element_id = str(uuid4())
        
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert_id}"
        ) as websocket:
            websocket.receive_text()  # Initial presence
            
            # Send lock request
            websocket.send_text(json.dumps({
                "type": MessageType.LOCK_ELEMENT.value,
                "element_id": element_id
            }))
            
            # Should receive lock acquired
            data = websocket.receive_text()
            message = json.loads(data)
            
            assert message["type"] == MessageType.LOCK_ACQUIRED.value
            assert message["element_id"] == element_id
    
    def test_lock_element_conflict(self, client, session_id):
        """Test element lock conflict when already locked."""
        expert1_id = str(uuid4())
        expert2_id = str(uuid4())
        element_id = str(uuid4())
        
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert1_id}"
        ) as ws1:
            ws1.receive_text()  # Initial presence
            
            # Expert 1 locks element
            ws1.send_text(json.dumps({
                "type": MessageType.LOCK_ELEMENT.value,
                "element_id": element_id
            }))
            ws1.receive_text()  # Lock acquired
            
            with client.websocket_connect(
                f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert2_id}"
            ) as ws2:
                ws2.receive_text()  # Initial presence
                ws1.receive_text()  # Participant joined
                
                # Expert 2 tries to lock same element
                ws2.send_text(json.dumps({
                    "type": MessageType.LOCK_ELEMENT.value,
                    "element_id": element_id
                }))
                
                # Should receive lock denied
                data = ws2.receive_text()
                message = json.loads(data)
                
                assert message["type"] == MessageType.LOCK_DENIED.value
                assert message["element_id"] == element_id
    
    def test_unlock_element(self, client, session_id, expert_id):
        """Test element unlocking."""
        element_id = str(uuid4())
        
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert_id}"
        ) as websocket:
            websocket.receive_text()  # Initial presence
            
            # Lock element
            websocket.send_text(json.dumps({
                "type": MessageType.LOCK_ELEMENT.value,
                "element_id": element_id
            }))
            websocket.receive_text()  # Lock acquired
            
            # Unlock element
            websocket.send_text(json.dumps({
                "type": MessageType.UNLOCK_ELEMENT.value,
                "element_id": element_id
            }))
            
            # Should receive lock released
            data = websocket.receive_text()
            message = json.loads(data)
            
            assert message["type"] == MessageType.LOCK_RELEASED.value
            assert message["element_id"] == element_id


# =============================================================================
# Heartbeat Tests
# =============================================================================

class TestHeartbeat:
    """Tests for heartbeat mechanism."""
    
    def test_heartbeat_response(self, client, session_id, expert_id):
        """Test heartbeat request and response."""
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert_id}"
        ) as websocket:
            websocket.receive_text()  # Initial presence
            
            # Send heartbeat
            websocket.send_text(json.dumps({
                "type": MessageType.HEARTBEAT.value
            }))
            
            # Should receive heartbeat ack
            data = websocket.receive_text()
            message = json.loads(data)
            
            assert message["type"] == MessageType.HEARTBEAT_ACK.value


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for WebSocket error handling."""
    
    def test_invalid_message_format(self, client, session_id, expert_id):
        """Test handling of invalid message format."""
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert_id}"
        ) as websocket:
            websocket.receive_text()  # Initial presence
            
            # Send invalid JSON
            websocket.send_text("not valid json")
            
            # Should receive error message
            data = websocket.receive_text()
            message = json.loads(data)
            
            assert message["type"] == MessageType.ERROR.value
            assert "error" in message.get("data", {})
    
    def test_unknown_message_type(self, client, session_id, expert_id):
        """Test handling of unknown message type."""
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert_id}"
        ) as websocket:
            websocket.receive_text()  # Initial presence
            
            # Send unknown message type
            websocket.send_text(json.dumps({
                "type": "unknown_type"
            }))
            
            # Should not crash, may log warning


# =============================================================================
# Concurrent Connection Tests
# =============================================================================

class TestConcurrentConnections:
    """Tests for concurrent WebSocket connections."""
    
    def test_multiple_participants(self, client, session_id):
        """Test multiple participants in same session."""
        expert_ids = [str(uuid4()) for _ in range(3)]
        
        # Connect all experts
        websockets = []
        for expert_id in expert_ids:
            ws = client.websocket_connect(
                f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert_id}"
            )
            ws.__enter__()
            websockets.append(ws)
            ws.receive_text()  # Initial presence
        
        try:
            # Verify all participants are tracked
            response = client.get(
                f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/participants"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 3
            
        finally:
            # Clean up
            for ws in websockets:
                ws.__exit__(None, None, None)
    
    def test_multiple_sessions(self, client):
        """Test connections to multiple sessions."""
        session1_id = str(uuid4())
        session2_id = str(uuid4())
        expert_id = str(uuid4())
        
        # Connect to session 1
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session1_id}/ws?expert_id={expert_id}"
        ) as ws1:
            ws1.receive_text()
            
            # Connect to session 2 with different expert
            expert2_id = str(uuid4())
            with client.websocket_connect(
                f"/api/v1/ontology-collaboration/collaboration/sessions/{session2_id}/ws?expert_id={expert2_id}"
            ) as ws2:
                ws2.receive_text()
                
                # Both sessions should be independent
                response1 = client.get(
                    f"/api/v1/ontology-collaboration/collaboration/sessions/{session1_id}/participants"
                )
                response2 = client.get(
                    f"/api/v1/ontology-collaboration/collaboration/sessions/{session2_id}/participants"
                )
                
                assert response1.json()["count"] == 1
                assert response2.json()["count"] == 1


# =============================================================================
# REST Endpoint Tests
# =============================================================================

class TestRESTEndpoints:
    """Tests for WebSocket-related REST endpoints."""
    
    def test_get_session_participants(self, client, session_id, expert_id):
        """Test getting session participants via REST."""
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert_id}"
        ) as websocket:
            websocket.receive_text()
            
            response = client.get(
                f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/participants"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            assert expert_id in data["participants"]
    
    def test_get_session_presence(self, client, session_id, expert_id):
        """Test getting session presence via REST."""
        with client.websocket_connect(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/ws?expert_id={expert_id}"
        ) as websocket:
            websocket.receive_text()
            
            response = client.get(
                f"/api/v1/ontology-collaboration/collaboration/sessions/{session_id}/presence"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            assert "participants" in data
            assert "active_locks" in data
