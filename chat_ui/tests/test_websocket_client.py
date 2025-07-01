"""Tests for the WebSocket client critical functionality."""
import asyncio
import json
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch

from chat_ui.websocket_client import ChatWebSocketClient, ConnectionState
from chat_ui.config import Config

@pytest.fixture
def mock_websockets():
    """Mock websockets library."""
    with patch('chat_ui.websocket_client.websockets') as mock_ws:
        mock_ws.connect = AsyncMock()
        mock_ws.exceptions.ConnectionClosed = Exception
        yield mock_ws

@pytest.fixture
async def websocket_client(mock_websockets):
    """WebSocket client fixture with mocked connections."""
    client = ChatWebSocketClient("ws://test")
    # Allow event loop to initialize
    await asyncio.sleep(0.1)
    return client

@pytest.mark.asyncio
async def test_connection_management(websocket_client, mock_websockets):
    """Test critical path: Connection management."""
    # Arrange
    mock_ws = AsyncMock()
    mock_websockets.connect.return_value = mock_ws
    
    # Act
    connected = await websocket_client._ensure_connected()
    
    # Assert
    assert connected is True
    assert websocket_client.get_connection_state() == ConnectionState.CONNECTED
    mock_websockets.connect.assert_called_once()

@pytest.mark.asyncio
async def test_reconnection_logic(websocket_client, mock_websockets):
    """Test critical path: Reconnection with backoff."""
    # Arrange
    mock_websockets.connect.side_effect = [
        Exception("Connection failed"),
        Exception("Still failed"),
        AsyncMock()  # Success on third try
    ]
    
    # Act
    await websocket_client._reconnect_with_backoff()
    
    # Assert
    assert mock_websockets.connect.call_count == 3
    assert websocket_client.get_connection_state() == ConnectionState.CONNECTED

@pytest.mark.asyncio
async def test_message_streaming(websocket_client):
    """Test critical path: Message streaming functionality."""
    # Arrange
    message = "Test message"
    message_id = "test-id"
    on_chunk = Mock()
    on_complete = Mock()
    
    websocket_client._websocket = AsyncMock()
    websocket_client._connection_state = ConnectionState.CONNECTED
    
    # Act
    await websocket_client._send_message_persistent(message, on_chunk, on_complete)
    
    # Assert
    websocket_client._websocket.send.assert_called_once()
    sent_data = json.loads(websocket_client._websocket.send.call_args[0][0])
    assert sent_data["type"] == "text_message"
    assert sent_data["content"] == message

@pytest.mark.asyncio
async def test_health_monitoring(websocket_client):
    """Test critical path: Connection health monitoring."""
    # Mock time to avoid actual waiting
    with patch('time.time') as mock_time:
        # Set up time progression
        mock_time.side_effect = [0, 1, 2, 3]  # Simulate time passing
        
        # Set up test conditions
        websocket_client._websocket = AsyncMock()
        websocket_client._connection_state = ConnectionState.CONNECTED
        websocket_client._last_ping_time = 0
        websocket_client._ping_interval = 1  # Short interval for testing
        
        # Set stop flag after one iteration
        async def stop_after_ping():
            await asyncio.sleep(0.1)  # Give monitor time to run once
            websocket_client._stop_health_monitor = True
        
        # Run monitor and stopper concurrently
        await asyncio.gather(
            websocket_client._health_monitor(),
            stop_after_ping()
        )
        
        # Assert ping was sent
        assert websocket_client._websocket.send.called
        sent_data = json.loads(websocket_client._websocket.send.call_args[0][0])
        assert sent_data["type"] == "ping"

@pytest.mark.asyncio
async def test_health_monitoring_reconnect(websocket_client):
    """Test critical path: Health monitoring triggers reconnect."""
    # Mock time to avoid actual waiting
    with patch('time.time') as mock_time:
        # Set up time progression to trigger health timeout
        mock_time.side_effect = [0, Config.HEALTH_CHECK_TIMEOUT + 1]
        
        # Set up test conditions
        websocket_client._websocket = AsyncMock()
        websocket_client._connection_state = ConnectionState.CONNECTED
        websocket_client._last_ping_time = 0
        websocket_client._ping_interval = 1  # Short interval for testing
        websocket_client._schedule_reconnect = AsyncMock()
        
        # Set stop flag after one iteration
        async def stop_after_check():
            await asyncio.sleep(0.1)  # Give monitor time to run once
            websocket_client._stop_health_monitor = True
        
        # Run monitor and stopper concurrently
        await asyncio.gather(
            websocket_client._health_monitor(),
            stop_after_check()
        )
        
        # Assert reconnect was scheduled
        assert websocket_client._connection_state == ConnectionState.DISCONNECTED
        websocket_client._schedule_reconnect.assert_called_once()

@pytest.mark.asyncio
async def test_message_handler(websocket_client):
    """Test critical path: Message handling and callbacks."""
    # Arrange
    message_id = "test-id"
    on_chunk = Mock()
    on_complete = Mock()
    websocket_client._message_handlers[message_id] = (on_chunk, on_complete)
    
    # Act - Test chunk handling
    chunk_data = {
        "type": "text_chunk",
        "id": message_id,
        "content": "test chunk"
    }
    await websocket_client._handle_message(chunk_data)
    
    # Assert
    on_chunk.assert_called_once_with("test chunk")
    
    # Act - Test completion
    complete_data = {
        "type": "message_complete",
        "id": message_id
    }
    await websocket_client._handle_message(complete_data)
    
    # Assert
    on_complete.assert_called_once()
    assert message_id not in websocket_client._message_handlers 