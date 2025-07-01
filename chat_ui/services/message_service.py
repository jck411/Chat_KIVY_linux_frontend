"""Message handling service for chat operations.

Handles all message operations including sending, receiving, streaming,
demo mode responses, error handling, and message history management.
"""

import threading
import time
from typing import Callable, Optional

from kivy.clock import Clock

from chat_ui.config import Config, Messages
from chat_ui.logging_config import get_logger, message_counter, message_latency, error_counter
from chat_ui.websocket_client import ChatWebSocketClient

# Set up structured logger for this module
logger = get_logger(__name__)

class MessageError(Exception):
    """Base class for message service errors."""

class MessageTooLongError(MessageError):
    """Message exceeds maximum allowed length."""

class MessageRateLimitError(MessageError):
    """Too many messages sent in a short time period."""

class MessageFormatError(MessageError):
    """Message format is invalid."""

class MessageServiceError(MessageError):
    """General message service error."""

class MessageService:
    """Service class that handles all message operations.
    
    Features:
    - Message sending with backend integration
    - Streaming text handling with batching
    - Demo mode responses
    - Error handling and user-friendly formatting
    - Message history management
    - Performance optimization with text batching
    """

    # Constants for validation
    MAX_MESSAGE_LENGTH = 4000  # Maximum characters per message
    MIN_MESSAGE_LENGTH = 1     # Minimum characters per message
    RATE_LIMIT_MESSAGES = 10   # Maximum messages per minute
    RATE_LIMIT_WINDOW = 60     # Rate limit window in seconds

    def __init__(self, websocket_client: ChatWebSocketClient) -> None:
        """Initialize the message service.
        
        Args:
            websocket_client: WebSocket client for backend communication
        """
        logger.info("initializing_message_service",
                   text_batch_ms=Config.TEXT_BATCH_MS,
                   max_messages=Config.MAX_MESSAGE_HISTORY)
        
        self.client = websocket_client
        self.current_bubble = None
        
        # Text batching for streaming optimization
        self._pending_chunks = []
        self._text_update_scheduled = False
        self._text_batch_delay = Config.TEXT_BATCH_MS / 1000.0
        
        # Memory management
        self.max_messages = Config.MAX_MESSAGE_HISTORY
        
        # Rate limiting
        self._message_timestamps = []
        
        # Callbacks (set by UI components)
        self._on_bubble_created = None
        self._on_bubble_updated = None
        self._on_focus_input = None
        self._on_scroll_bottom = None
        self._on_cleanup_messages = None

    def set_ui_callbacks(self, 
                        on_bubble_created: Callable,
                        on_bubble_updated: Callable,
                        on_focus_input: Callable,
                        on_scroll_bottom: Callable,
                        on_cleanup_messages: Callable) -> None:
        """Set UI callback functions for message service to interact with UI.
        
        Args:
            on_bubble_created: Callback when new message bubble is created
            on_bubble_updated: Callback when bubble text is updated
            on_focus_input: Callback to focus input field
            on_scroll_bottom: Callback to scroll to bottom
            on_cleanup_messages: Callback to cleanup old messages
        """
        self._on_bubble_created = on_bubble_created
        self._on_bubble_updated = on_bubble_updated
        self._on_focus_input = on_focus_input
        self._on_scroll_bottom = on_scroll_bottom
        self._on_cleanup_messages = on_cleanup_messages

    def _validate_message(self, text: str) -> None:
        """Validate message before sending.
        
        Args:
            text: Message text to validate
            
        Raises:
            MessageTooLongError: If message exceeds length limit
            MessageFormatError: If message format is invalid
            MessageRateLimitError: If rate limit exceeded
        """
        # Check message length
        if len(text) > self.MAX_MESSAGE_LENGTH:
            error_counter.inc()
            msg = f"Message too long ({len(text)} chars). Maximum is {self.MAX_MESSAGE_LENGTH}."
            raise MessageTooLongError(msg)
            
        if len(text.strip()) < self.MIN_MESSAGE_LENGTH:
            error_counter.inc()
            msg = "Message cannot be empty."
            raise MessageFormatError(msg)
            
        # Check rate limiting
        current_time = time.time()
        self._message_timestamps = [
            ts for ts in self._message_timestamps 
            if current_time - ts < self.RATE_LIMIT_WINDOW
        ]
        
        if len(self._message_timestamps) >= self.RATE_LIMIT_MESSAGES:
            error_counter.inc()
            msg = f"Rate limit exceeded. Maximum {self.RATE_LIMIT_MESSAGES} messages per {self.RATE_LIMIT_WINDOW} seconds."
            raise MessageRateLimitError(msg)
            
        self._message_timestamps.append(current_time)

    def send_message(self, text: str, backend_available: bool, total_messages: int) -> None:
        """Handle message sending with backend or demo mode.
        
        Args:
            text: Message text to send
            backend_available: Whether backend connection is available
            total_messages: Current total number of messages (for logging)
        """
        if not text:
            return

        # Track message metrics
        message_counter.inc()
        start_time = time.time()

        try:
            # Validate message
            self._validate_message(text)

            logger.info("sending_message",
                       message_length=len(text),
                       backend_available=backend_available,
                       total_messages=total_messages)

            # Cleanup old messages if needed
            if self._on_cleanup_messages:
                self._on_cleanup_messages()

            # Scroll to bottom
            if self._on_scroll_bottom:
                self._on_scroll_bottom(force=True)

            # Reset current bubble for new response
            self.current_bubble = None

            if backend_available:
                self._send_to_backend(text)
            else:
                self._show_demo_response(text)

            # Record message latency
            message_latency.observe(time.time() - start_time)
        except MessageError as e:
            error_counter.inc()
            logger.warning("message_validation_failed", error=str(e))
            raise
        except Exception as e:
            error_counter.inc()
            logger.exception("message_send_failed", error=str(e))
            raise MessageServiceError(f"Failed to send message: {e}")

    def _send_to_backend(self, message: str) -> None:
        """Send message to backend in background thread.
        
        Args:
            message: Message to send to backend
        """
        thread = threading.Thread(target=self._threaded_send, args=(message,), daemon=True)
        thread.start()

    def _show_demo_response(self, message: str) -> None:
        """Show demo response when backend is unavailable.
        
        Args:
            message: Original user message
        """
        logger.info("showing_demo_response", original_message_length=len(message))
        demo_text = Messages.DEMO_RESPONSE.format(message=message)
        
        if self._on_bubble_created:
            self._on_bubble_created(demo_text, is_user=False)
        
        if self._on_scroll_bottom:
            self._on_scroll_bottom(force=True)
            
        Clock.schedule_once(lambda dt: self._focus_input(), 0.5)

    def _threaded_send(self, message: str) -> None:
        """Send message to backend with error handling.
        
        Args:
            message: Message to send
        """
        start_time = time.time()
        try:
            logger.info("sending_to_backend", message_length=len(message))
            self.client.send_message_sync(message, self._on_chunk, self._on_message_complete)
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info("backend_send_completed", elapsed_ms=elapsed_ms)
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            error_msg = self._format_error_message(str(e))
            logger.exception("backend_send_failed", error=str(e), elapsed_ms=elapsed_ms)
            Clock.schedule_once(lambda dt: self._show_error_message(error_msg))

    def _show_error_message(self, error_msg: str) -> None:
        """Show error message on main thread.
        
        Args:
            error_msg: Formatted error message to display
        """
        try:
            logger.warning("displaying_error_message", error=error_msg)
            error_text = f"❌ {error_msg}"
            
            if self._on_bubble_created:
                self._on_bubble_created(error_text, is_user=False)
            
            if self._on_scroll_bottom:
                self._on_scroll_bottom(force=True)
                
            self._focus_input()
        except Exception as e:
            # Fallback - let UI handle this
            logger.exception("error_display_failed", error=str(e), original_error=error_msg)
            raise Exception(f"Error display failed: {e}")

    def _format_error_message(self, error: str) -> str:
        """Format error messages to be user-friendly.
        
        Args:
            error: Raw error message
            
        Returns:
            User-friendly error message
        """
        error_lower = error.lower()
        if "timeout" in error_lower:
            return Messages.TIMEOUT
        elif "connection refused" in error_lower:
            return Messages.CONNECTION_REFUSED
        elif "failed after" in error_lower:
            return Messages.MAX_RETRIES
        else:
            return Messages.UNKNOWN_ERROR.format(error=error)

    def _on_chunk(self, chunk: str) -> None:
        """Handle incoming chunk with batching for better performance.
        
        Args:
            chunk: Text chunk received from backend
        """
        self._pending_chunks.append(chunk)

        if not self._text_update_scheduled:
            self._text_update_scheduled = True
            Clock.schedule_once(self._process_batched_chunks, self._text_batch_delay)

    def _process_batched_chunks(self, dt) -> None:
        """Process all pending chunks in a single UI update."""
        if self._pending_chunks:
            combined_text = "".join(self._pending_chunks)
            self._pending_chunks.clear()
            self._append_chunk_batch(combined_text)

        self._text_update_scheduled = False

    def _on_message_complete(self) -> None:
        """Called when the assistant finishes responding."""
        # Process any remaining chunks immediately
        if self._pending_chunks:
            combined_text = "".join(self._pending_chunks)
            self._pending_chunks.clear()
            self._append_chunk_batch(combined_text)
            self._text_update_scheduled = False

        Clock.schedule_once(lambda dt: self._focus_input())

    def _focus_input(self) -> None:
        """Focus the text input field."""
        if self._on_focus_input:
            self._on_focus_input()

    def _append_chunk_batch(self, text: str) -> None:
        """Append batched text to the current bubble with optimized scrolling.
        
        Args:
            text: Text to append to current bubble
        """
        # Create bubble on first chunk
        if not self.current_bubble:
            if self._on_bubble_created:
                self.current_bubble = self._on_bubble_created(text, is_user=False)
            if self._on_scroll_bottom:
                self._on_scroll_bottom(force=True)
        else:
            # Append to existing bubble using the bubble's append method
            self.current_bubble.append_text(text)
            if self._on_scroll_bottom:
                self._on_scroll_bottom()

    def cleanup_old_messages(self, current_message_count: int) -> int:
        """Remove old messages to prevent memory bloat during long conversations.
        
        Args:
            current_message_count: Current number of messages
            
        Returns:
            Number of messages that should be removed
        """
        if current_message_count > self.max_messages:
            messages_to_remove = current_message_count - self.max_messages
            logger.info("cleaning_up_old_messages",
                       total_messages=current_message_count,
                       removing_count=messages_to_remove,
                       max_allowed=self.max_messages)
            return messages_to_remove
        return 0

    def reset_current_bubble(self) -> None:
        """Reset the current bubble (call when starting new conversation)."""
        self.current_bubble = None 