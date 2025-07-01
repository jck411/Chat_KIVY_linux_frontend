"""Tests for the MessageService critical path functionality."""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from chat_ui.services.message_service import MessageService
from chat_ui.config import Config

@pytest.fixture
def websocket_client():
    """Mock websocket client fixture."""
    client = Mock()
    client.send_message_sync = Mock()
    return client

@pytest.fixture
def message_service(websocket_client):
    """MessageService fixture with mocked dependencies."""
    service = MessageService(websocket_client)
    # Mock UI callbacks
    service._on_bubble_created = Mock()
    service._on_bubble_updated = Mock()
    service._on_focus_input = Mock()
    service._on_scroll_bottom = Mock()
    service._on_cleanup_messages = Mock()
    return service

@pytest.mark.asyncio
async def test_send_message_with_backend(message_service, websocket_client):
    """Test critical path: Message sending with backend available."""
    # Arrange
    test_message = "Test message"
    websocket_client.send_message_sync.return_value = "Message sent successfully"
    
    # Act
    message_service.send_message(test_message, backend_available=True, total_messages=1)
    
    # Assert
    websocket_client.send_message_sync.assert_called_once()
    message_service._on_bubble_created.assert_not_called()  # Should be called by websocket response

@pytest.mark.asyncio
async def test_send_message_demo_mode(message_service, websocket_client):
    """Test critical path: Message sending in demo mode."""
    # Arrange
    test_message = "Test message"
    
    # Act
    message_service.send_message(test_message, backend_available=False, total_messages=1)
    
    # Assert
    websocket_client.send_message_sync.assert_not_called()
    message_service._on_bubble_created.assert_called_once()

def test_cleanup_old_messages(message_service):
    """Test critical path: Message history management."""
    # Arrange
    current_count = Config.MAX_MESSAGE_HISTORY + 5
    
    # Act
    to_remove = message_service.cleanup_old_messages(current_count)
    
    # Assert
    assert to_remove == 5

@pytest.mark.asyncio
async def test_text_batching(message_service):
    """Test critical path: Text batching optimization."""
    # Arrange
    chunks = ["Hello", " ", "World"]
    
    # Act
    for chunk in chunks:
        message_service._on_chunk(chunk)
    await asyncio.sleep(Config.TEXT_BATCH_MS / 1000.0 + 0.1)
    
    # Assert
    assert len(message_service._pending_chunks) == 0  # Chunks should be processed

def test_error_handling(message_service, websocket_client):
    """Test critical path: Error handling and formatting."""
    # Arrange
    test_message = "Test message"
    websocket_client.send_message_sync.side_effect = Exception("Connection refused")
    
    # Act
    message_service.send_message(test_message, backend_available=True, total_messages=1)
    
    # Assert
    message_service._on_bubble_created.assert_called_once()
    args = message_service._on_bubble_created.call_args[0]
    assert "❌" in args[0]  # Error message should contain error indicator 