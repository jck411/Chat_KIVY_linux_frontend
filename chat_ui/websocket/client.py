"""Main WebSocket client implementation.

This module provides the main WebSocket client that integrates
all the modular components into a cohesive system.
"""

import asyncio
import json
import threading
import time
from typing import Optional, Callable, Dict, Any

from chat_ui.config import Config
from chat_ui.logging_config import get_logger, message_counter, message_latency

from .connection_manager import ConnectionManager, ConnectionState
from .health_monitor import HealthMonitor
from .message_handler import MessageHandler, MessageHandlerError
from .reconnection_manager import ReconnectionManager

# Set up structured logger for this module
logger = get_logger(__name__)

class WebSocketClient:
    """Production WebSocket client with modular components.
    
    Features:
    - Persistent connections with automatic reconnection
    - Thread-safe operations with background event loop
    - Connection health monitoring with ping/pong
    - Message streaming with chunk batching
    - Exponential backoff retry logic
    - Clean logging for production use
    """

    def __init__(self, uri: Optional[str] = None) -> None:
        """Initialize WebSocket client.
        
        Args:
            uri: Optional WebSocket server URI (defaults to Config.WEBSOCKET_URI)
        """
        self.uri = uri or Config.WEBSOCKET_URI
        
        # Initialize event loop and threading
        self._loop = None
        self._thread = None
        self._setup_background_loop()

        # Initialize components
        self._connection = ConnectionManager(
            self.uri,
            self._get_connect_kwargs()
        )
        
        # Set up message handling
        self._message_handler = MessageHandler()
        self._connection.on_message = self._message_handler.handle_message
        
        self._health_monitor = HealthMonitor(
            Config.PING_INTERVAL,
            Config.HEALTH_CHECK_TIMEOUT,
            self._handle_unhealthy_connection,
            self._send_raw_message
        )
        
        self._reconnection = ReconnectionManager(
            Config.MAX_RETRIES,
            Config.RETRY_DELAY,
            self._connection.connect
        )

        # Start health monitoring if enabled
        if Config.CONNECTION_HEALTH_CHECK:
            asyncio.run_coroutine_threadsafe(
                self._health_monitor.start(),
                self._loop
            )

    def _get_connect_kwargs(self) -> Dict[str, Any]:
        """Get connection configuration parameters."""
        return {
            "ping_interval": 20,
            "ping_timeout": 10,
            "max_size": 2**20,  # 1MB max message size
        }

    def _setup_background_loop(self) -> None:
        """Set up background event loop for async operations."""
        def run_loop() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._thread = threading.Thread(
            target=run_loop,
            daemon=True,
            name="WSClient"
        )
        self._thread.start()

        # Wait for loop to be ready
        timeout = time.time() + 5
        while self._loop is None and time.time() < timeout:
            threading.Event().wait(0.01)

        if self._loop is None:
            msg = "Failed to initialize WebSocket client event loop"
            raise RuntimeError(msg)

    async def _handle_unhealthy_connection(self) -> None:
        """Handle unhealthy connection state."""
        logger.warning("unhealthy_connection_detected")
        await self._reconnection.start_reconnect()

    async def _send_raw_message(self, message: str) -> None:
        """Send raw message through websocket.
        
        Args:
            message: Raw message string to send
        """
        if self._connection.websocket:
            await self._connection.websocket.send(message)

    def send_message_sync(
        self,
        message: str,
        on_chunk: Callable[[str], None],
        on_complete: Optional[Callable[[], None]] = None
    ) -> str:
        """Send message using persistent connection (synchronous wrapper).
        
        Args:
            message: Message content to send
            on_chunk: Callback for receiving message chunks
            on_complete: Optional callback for message completion
            
        Returns:
            Success message string
            
        Raises:
            Exception: If message sending fails
        """
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._send_message(message, on_chunk, on_complete),
                self._loop
            )
            return future.result(timeout=Config.CONNECTION_TIMEOUT)
        except Exception as e:
            msg = f"Message send failed: {e}"
            raise Exception(msg)

    async def _send_message(
        self,
        message: str,
        on_chunk: Callable[[str], None],
        on_complete: Optional[Callable[[], None]] = None
    ) -> str:
        """Send message asynchronously.
        
        Args:
            message: Message content to send
            on_chunk: Callback for receiving message chunks
            on_complete: Optional callback for message completion
            
        Returns:
            Success message string
        """
        message_id = self._message_handler.register_handler(on_chunk, on_complete)
        start_time = time.time()

        try:
            message_data = {
                "type": "text_message",
                "id": message_id,
                "content": message,
            }
            await self._send_raw_message(json.dumps(message_data))
            message_latency.observe(time.time() - start_time)
            return "Message sent successfully"
            
        except Exception as e:
            self._message_handler.remove_handler(message_id)
            raise

    def test_connection_sync(self) -> bool:
        """Test if backend connection is available (synchronous wrapper)."""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._connection.connect(),
                self._loop
            )
            future.result(timeout=Config.CONNECTION_TEST_TIMEOUT)
            return True
        except Exception:
            return False

    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection.state

    async def close(self) -> None:
        """Clean shutdown of WebSocket client."""
        logger.info("shutting_down_websocket_client")
        
        # Stop health monitoring
        await self._health_monitor.stop()
        
        # Stop reconnection attempts
        await self._reconnection.stop()
        
        # Close connection
        await self._connection.close()
        
        # Stop event loop
        self._loop.stop()
        logger.info("websocket_client_shutdown_complete") 