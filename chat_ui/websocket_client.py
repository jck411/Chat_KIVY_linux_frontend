"""WebSocket client for connecting to the backend chat service
Optimized with persistent connection management for production use.
"""

import asyncio
import json
import threading
import time
import uuid
from enum import Enum
from typing import Callable, Optional

import websockets

from chat_ui.config import Config
from chat_ui.logging_config import get_logger

# Set up structured logger for this module
logger = get_logger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration for WebSocket client."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ChatWebSocketClient:
    """Production-ready WebSocket client with persistent connection management.

    Features:
    - Persistent connections with automatic reconnection
    - Thread-safe operations with background event loop
    - Connection health monitoring with ping/pong
    - Message streaming with chunk batching
    - Exponential backoff retry logic
    - Clean logging for production use
    """

    def __init__(self, uri: Optional[str] = None) -> None:
        self.uri = uri or Config.WEBSOCKET_URI
        self.max_retries = Config.MAX_RETRIES
        self.retry_delay = Config.RETRY_DELAY

        # Event loop and threading
        self._loop = None
        self._thread = None

        # Persistent connection management
        self._websocket = None
        self._connection_lock = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._reconnect_task = None

        # Connection health monitoring
        self._last_ping_time = 0
        self._ping_interval = Config.PING_INTERVAL
        self._health_check_task = None
        self._stop_health_monitor = False  # Flag to stop health monitor

        # Message handling
        self._message_handlers = {}  # message_id -> (on_chunk, on_complete)

        self._start_background_loop()

    def _start_background_loop(self) -> None:
        """Start a background thread with persistent event loop."""
        def run_loop() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            # Initialize async primitives in the loop
            self._connection_lock = asyncio.Lock()

            # Start health monitoring only if enabled (can be disabled for production)
            if Config.CONNECTION_HEALTH_CHECK:
                self._health_check_task = self._loop.create_task(self._health_monitor())
                logger.info(f"💓 Health monitoring enabled (interval: {self._ping_interval}s)")
            else:
                logger.info("🔇 Health monitoring disabled - relying on WebSocket built-in keepalive")

            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True, name="WSClient")
        self._thread.start()

        # Wait for loop to be ready with timeout
        timeout = time.time() + 5
        while (self._loop is None or self._connection_lock is None) and time.time() < timeout:
            threading.Event().wait(0.01)

        if self._loop is None:
            msg = "Failed to initialize WebSocket client event loop"
            raise RuntimeError(msg)

    def send_message_sync(self, message: str, on_chunk: Callable[[str], None],
                         on_complete: Optional[Callable[[], None]] = None) -> str:
        """Send message using persistent connection (synchronous wrapper).

        Args:
        ----
            message: The message content to send
            on_chunk: Callback function for receiving streaming chunks
            on_complete: Optional callback when message is complete

        Returns:
        -------
            Success message string

        Raises:
        ------
            Exception: If message sending fails after retries

        """
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._send_message_persistent(message, on_chunk, on_complete),
                self._loop,
            )
            return future.result(timeout=Config.CONNECTION_TIMEOUT)
        except Exception as e:
            msg = f"Message send failed: {e!s}"
            raise Exception(msg)

    def test_connection_sync(self) -> bool:
        """Test if backend connection is available (synchronous wrapper)."""
        try:
            future = asyncio.run_coroutine_threadsafe(self._test_connection_persistent(), self._loop)
            return future.result(timeout=Config.CONNECTION_TEST_TIMEOUT)
        except Exception:
            return False

    def get_connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection_state

    async def _ensure_connected(self) -> bool:
        """Ensure we have a healthy persistent connection."""
        async with self._connection_lock:
            if self._websocket is None or self._is_connection_closed():
                await self._connect()
            return self._connection_state == ConnectionState.CONNECTED

    def _is_connection_closed(self) -> bool:
        """Check if websocket connection is closed (compatible with websockets 15.0.1)."""
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

    async def _connect(self) -> None:
        """Establish persistent WebSocket connection with fallback options."""
        if self._connection_state == ConnectionState.CONNECTING:
            return

        self._connection_state = ConnectionState.CONNECTING
        logger.info("connecting_to_websocket", uri=self.uri)

        try:
            # Close existing connection if any
            if self._websocket and not self._is_connection_closed():
                await self._websocket.close()

            # Connection settings
            connect_kwargs = {
                "ping_interval": 20,
                "ping_timeout": 10,
                "max_size": 2**20,  # 1MB max message size
            }

            # Try with compression first, fallback without if it fails
            try:
                connect_kwargs["compression"] = "deflate"
                self._websocket = await websockets.connect(self.uri, **connect_kwargs)
                logger.info("websocket_connected", compression=True)
            except Exception as e:
                # Fallback without compression
                connect_kwargs.pop("compression", None)
                self._websocket = await websockets.connect(self.uri, **connect_kwargs)
                logger.info("websocket_connected", compression=False, fallback_reason=str(e))

            self._connection_state = ConnectionState.CONNECTED
            self._last_ping_time = time.time()

            # Start message listener
            self._loop.create_task(self._message_listener())

        except Exception as e:
            self._connection_state = ConnectionState.FAILED
            logger.exception("websocket_connection_failed", error=str(e), uri=self.uri)
            msg = f"Failed to connect to {self.uri}: {e}"
            raise ConnectionError(msg)

    async def _message_listener(self) -> None:
        """Listen for incoming messages on persistent connection."""
        try:
            async for raw_message in self._websocket:
                try:
                    data = json.loads(raw_message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    continue  # Skip invalid JSON silently
                except Exception as e:
                    logger.warning(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("🔄 Connection closed, attempting reconnect")
            self._connection_state = ConnectionState.DISCONNECTED
            await self._schedule_reconnect()
        except Exception as e:
            logger.exception(f"❌ Message listener error: {e}")
            self._connection_state = ConnectionState.FAILED
            await self._schedule_reconnect()

    async def _handle_message(self, data: dict) -> None:
        """Handle incoming WebSocket message efficiently."""
        message_type = data.get("type")
        message_id = data.get("id") or data.get("message_id")

        if message_type == "text_chunk" and message_id in self._message_handlers:
            chunk = data.get("content", "")
            on_chunk, _ = self._message_handlers[message_id]
            if on_chunk:
                on_chunk(chunk)

        elif message_type == "message_complete" and message_id in self._message_handlers:
            _, on_complete = self._message_handlers[message_id]
            if on_complete:
                on_complete()
            # Clean up handler
            del self._message_handlers[message_id]

        elif message_type == "error" and message_id in self._message_handlers:
            # Clean up handler on error
            del self._message_handlers[message_id]
            error_msg = data.get("content", "Unknown error")
            logger.error(f"Backend error: {error_msg}")
            msg = f"Backend error: {error_msg}"
            raise Exception(msg)

        elif message_type == "pong":
            self._last_ping_time = time.time()

    async def _send_message_persistent(self, message: str, on_chunk: Callable[[str], None],
                                     on_complete: Optional[Callable[[], None]] = None) -> str:
        """Send message using persistent connection with retry logic."""
        message_id = str(uuid.uuid4())

        # Store message handlers
        self._message_handlers[message_id] = (on_chunk, on_complete)

        for attempt in range(self.max_retries + 1):
            try:
                # Ensure we have a connection
                if not await self._ensure_connected():
                    msg = "Failed to establish connection"
                    raise ConnectionError(msg)

                # Send message
                message_data = {
                    "type": "text_message",
                    "id": message_id,
                    "content": message,
                }

                await self._websocket.send(json.dumps(message_data))
                # Debug logging disabled for production - uncomment for debugging:
                # logger.debug(f"📤 Message sent: {message[:50]}...")
                return "Message sent successfully"

            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"Send attempt {attempt + 1} failed, retrying: {e}")
                    # Wait before retry with exponential backoff
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    # Force reconnection on next attempt
                    self._connection_state = ConnectionState.DISCONNECTED
                else:
                    # Clean up handler on final failure
                    self._message_handlers.pop(message_id, None)
                    logger.exception(f"Message send failed after {self.max_retries + 1} attempts")
                    msg = f"Failed after {self.max_retries + 1} attempts: {e}"
                    raise Exception(msg)
        return None

    async def _schedule_reconnect(self) -> None:
        """Schedule reconnection attempt."""
        if self._reconnect_task and not self._reconnect_task.done():
            return  # Reconnection already scheduled

        self._connection_state = ConnectionState.RECONNECTING
        logger.info("🔄 Scheduling reconnection")
        self._reconnect_task = self._loop.create_task(self._reconnect_with_backoff())

    async def _reconnect_with_backoff(self) -> None:
        """Reconnect with exponential backoff."""
        for attempt in range(self.max_retries):
            try:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                await self._connect()
                logger.info(f"✅ Reconnected after {attempt + 1} attempts")
                return
            except Exception as e:
                logger.warning(f"Reconnect attempt {attempt + 1} failed: {e}")
                continue

        logger.error(f"❌ Failed to reconnect after {self.max_retries} attempts")
        self._connection_state = ConnectionState.FAILED

    async def _health_monitor(self) -> None:
        """Monitor connection health and send periodic pings."""
        while not self._stop_health_monitor:
            try:
                await asyncio.sleep(self._ping_interval)

                if self._connection_state == ConnectionState.CONNECTED and self._websocket:
                    current_time = time.time()

                    # Check if we haven't received a pong recently (using configurable timeout)
                    health_timeout = Config.HEALTH_CHECK_TIMEOUT
                    if current_time - self._last_ping_time > health_timeout:
                        logger.warning("💔 Connection appears stale, reconnecting")
                        self._connection_state = ConnectionState.DISCONNECTED
                        await self._schedule_reconnect()
                    else:
                        # Send ping to keep connection alive
                        try:
                            ping_data = {"type": "ping", "timestamp": current_time}
                            await self._websocket.send(json.dumps(ping_data))
                        except Exception as e:
                            logger.warning(f"Health check failed: {e}")
                            await self._schedule_reconnect()

            except Exception as e:
                logger.exception(f"Health monitor error: {e}")
                await asyncio.sleep(self._ping_interval)

    async def _test_connection_persistent(self) -> bool:
        """Test connection using persistent connection."""
        try:
            return await self._ensure_connected()
        except Exception:
            return False

    async def close(self) -> None:
        """Clean shutdown of WebSocket client."""
        logger.info("🔄 Closing WebSocket client")

        self._stop_health_monitor = True  # Signal health monitor to stop
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        if self._websocket and not self._is_connection_closed():
            await self._websocket.close()

        self._connection_state = ConnectionState.DISCONNECTED
        logger.info("✅ WebSocket client closed")
