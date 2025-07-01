"""Message handling for WebSocket communication.

This module manages message processing and callback handling
for the WebSocket client.
"""

import json
import uuid
from typing import Callable, Dict, Optional, Tuple, Any, Coroutine

from chat_ui.logging_config import get_logger, message_counter, error_counter

# Set up structured logger for this module
logger = get_logger(__name__)

class MessageHandlerError(Exception):
    """Base class for message handler errors."""

class InvalidMessageError(MessageHandlerError):
    """Invalid message format or content."""

class MessageHandler:
    """Handles WebSocket message processing and callback management.
    
    Features:
    - Message ID generation and tracking
    - Callback registration and cleanup
    - Structured message processing
    - Error handling and logging
    """

    def __init__(self) -> None:
        """Initialize message handler."""
        self._handlers: Dict[
            str,
            Tuple[Callable[[str], None], Optional[Callable[[], None]]]
        ] = {}

    def register_handler(
        self,
        on_chunk: Callable[[str], None],
        on_complete: Optional[Callable[[], None]] = None
    ) -> str:
        """Register message handlers and return message ID.
        
        Args:
            on_chunk: Callback for handling message chunks
            on_complete: Optional callback for message completion
            
        Returns:
            Unique message ID for tracking
        """
        message_id = str(uuid.uuid4())
        self._handlers[message_id] = (on_chunk, on_complete)
        return message_id

    def remove_handler(self, message_id: str) -> None:
        """Remove message handler.
        
        Args:
            message_id: ID of handler to remove
        """
        self._handlers.pop(message_id, None)

    async def handle_message(self, raw_message: str) -> None:
        """Process incoming message.
        
        Args:
            raw_message: Raw message string to process
            
        Raises:
            InvalidMessageError: If message format is invalid
        """
        try:
            data = json.loads(raw_message)
            message_type = data.get("type")
            message_id = data.get("id") or data.get("message_id")

            if message_id in self._handlers:
                await self._process_message(message_type, message_id, data)
                
        except json.JSONDecodeError as e:
            logger.warning("invalid_json_message", error=str(e))
            error_counter.inc()
            raise InvalidMessageError(f"Invalid JSON: {e}")
        except Exception as e:
            logger.exception("message_processing_error", error=str(e))
            error_counter.inc()
            raise

    async def _process_message(self, message_type: str, message_id: str, data: dict) -> None:
        """Process specific message type.
        
        Args:
            message_type: Type of message to process
            message_id: Message ID for handler lookup
            data: Message data dictionary
            
        Raises:
            InvalidMessageError: If message type is invalid
            MessageHandlerError: If processing fails
        """
        try:
            if message_type == "text_chunk":
                chunk = data.get("content", "")
                on_chunk, _ = self._handlers[message_id]
                if on_chunk:
                    on_chunk(chunk)
                    message_counter.inc()

            elif message_type == "message_complete":
                _, on_complete = self._handlers[message_id]
                if on_complete:
                    on_complete()
                self.remove_handler(message_id)

            elif message_type == "error":
                self.remove_handler(message_id)
                error_msg = data.get("content", "Unknown error")
                logger.error("backend_error", error=error_msg)
                error_counter.inc()
                raise MessageHandlerError(f"Backend error: {error_msg}")

            else:
                logger.warning("unknown_message_type",
                             message_type=message_type,
                             message_id=message_id)
                
        except Exception as e:
            logger.exception("message_processing_failed",
                           message_type=message_type,
                           message_id=message_id,
                           error=str(e))
            error_counter.inc()
            raise 