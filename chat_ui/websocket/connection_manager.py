"""Connection management for WebSocket client.

This module handles the WebSocket connection lifecycle and state management.
"""

import asyncio
from enum import Enum
from typing import Optional, Dict, Any, Callable, Coroutine

import websockets
from websockets.client import WebSocketClientProtocol

from chat_ui.logging_config import get_logger, websocket_state

# Set up structured logger for this module
logger = get_logger(__name__)

class ConnectionState(Enum):
    """Connection state enumeration for WebSocket client."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"

class ConnectionManager:
    """Manages WebSocket connection lifecycle with state tracking.
    
    Features:
    - Connection establishment with compression
    - State management
    - Connection health checks
    - Clean connection shutdown
    """

    def __init__(self, uri: str, connect_kwargs: Dict[str, Any]) -> None:
        """Initialize connection manager.
        
        Args:
            uri: WebSocket server URI
            connect_kwargs: Connection configuration parameters
        """
        self._uri = uri
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._state = ConnectionState.DISCONNECTED
        self._connect_kwargs = connect_kwargs
        self._lock = asyncio.Lock()
        self._listener_task: Optional[asyncio.Task] = None
        # Callback for handling incoming messages
        self.on_message: Optional[Callable[[str], Coroutine[Any, Any, None]]] = None

    async def connect(self) -> None:
        """Establish connection with compression fallback."""
        async with self._lock:
            if self._state == ConnectionState.CONNECTING:
                return

            self._state = ConnectionState.CONNECTING
            websocket_state.inc()  # Track state change
            logger.info("connecting_to_websocket", uri=self._uri)

            try:
                if self._websocket and not self.is_closed:
                    await self._websocket.close()

                # Try with compression first
                try:
                    self._connect_kwargs["compression"] = "deflate"
                    self._websocket = await websockets.connect(
                        self._uri,
                        **self._connect_kwargs
                    )
                    logger.info("websocket_connected", compression=True)
                except Exception as e:
                    # Fallback without compression
                    self._connect_kwargs.pop("compression", None)
                    self._websocket = await websockets.connect(
                        self._uri,
                        **self._connect_kwargs
                    )
                    logger.info("websocket_connected",
                              compression=False,
                              fallback_reason=str(e))

                self._state = ConnectionState.CONNECTED
                websocket_state.inc()  # Track state change

                # Start message listener
                if self._listener_task:
                    self._listener_task.cancel()
                self._listener_task = asyncio.create_task(self._message_listener())
                logger.info("message_listener_started")

            except Exception as e:
                self._state = ConnectionState.FAILED
                websocket_state.inc()  # Track state change
                logger.exception("websocket_connection_failed",
                               error=str(e),
                               uri=self._uri)
                raise ConnectionError(f"Failed to connect to {self._uri}: {e}")

    async def _message_listener(self) -> None:
        """Listen for incoming messages on the WebSocket connection."""
        if not self._websocket:
            return

        try:
            async for message in self._websocket:
                try:
                    if self.on_message:
                        await self.on_message(message)
                    else:
                        logger.warning("no_message_handler_configured")
                except Exception as e:
                    logger.exception("message_processing_error", error=str(e))

        except websockets.exceptions.ConnectionClosed:
            logger.warning("websocket_connection_closed")
            self._state = ConnectionState.DISCONNECTED
            websocket_state.inc()
        except Exception as e:
            logger.exception("message_listener_error", error=str(e))
            self._state = ConnectionState.FAILED
            websocket_state.inc()

    @property
    def is_closed(self) -> bool:
        """Check if connection is closed."""
        if self._websocket is None:
            return True

        try:
            # Multiple methods to check connection state for compatibility
            if hasattr(self._websocket, "close_code") and self._websocket.close_code is not None:
                return True
            if hasattr(self._websocket, "closed") and self._websocket.closed:
                return True
            if hasattr(self._websocket, "state") and str(self._websocket.state) in ["CLOSED", "CLOSING"]:
                return True
            return False
        except Exception:
            return True

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def websocket(self) -> Optional[WebSocketClientProtocol]:
        """Get websocket instance."""
        return self._websocket

    async def close(self) -> None:
        """Close the connection cleanly."""
        async with self._lock:
            if self._listener_task:
                self._listener_task.cancel()
                try:
                    await self._listener_task
                except asyncio.CancelledError:
                    pass
                self._listener_task = None

            if self._websocket and not self.is_closed:
                await self._websocket.close()
            self._state = ConnectionState.DISCONNECTED
            websocket_state.inc()  # Track state change 