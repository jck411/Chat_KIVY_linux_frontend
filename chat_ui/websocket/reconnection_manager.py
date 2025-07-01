"""Reconnection management for WebSocket client.

This module handles reconnection attempts with exponential backoff
and proper error handling.
"""

import asyncio
from typing import Callable, Coroutine, Any, Optional

from chat_ui.logging_config import get_logger, error_counter

# Set up structured logger for this module
logger = get_logger(__name__)

class ReconnectionManager:
    """Manages reconnection attempts with exponential backoff.
    
    Features:
    - Exponential backoff retry strategy
    - Configurable retry limits
    - Clean cancellation support
    - Detailed logging
    """

    def __init__(
        self,
        max_retries: int,
        retry_delay: float,
        connect_func: Callable[[], Coroutine[Any, Any, None]]
    ) -> None:
        """Initialize reconnection manager.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (will be exponentially increased)
            connect_func: Async function to attempt connection
        """
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._connect_func = connect_func
        self._reconnect_task: Optional[asyncio.Task] = None

    async def start_reconnect(self) -> None:
        """Start reconnection process if not already running."""
        if self._reconnect_task and not self._reconnect_task.done():
            logger.info("reconnection_already_in_progress")
            return

        logger.info("scheduling_reconnection",
                   max_retries=self._max_retries,
                   base_delay=self._retry_delay)
        self._reconnect_task = asyncio.create_task(self._reconnect_with_backoff())

    async def stop(self) -> None:
        """Stop reconnection attempts cleanly."""
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

    async def _reconnect_with_backoff(self) -> None:
        """Attempt reconnection with exponential backoff."""
        for attempt in range(self._max_retries):
            try:
                # Calculate delay with exponential backoff
                delay = self._retry_delay * (2 ** attempt)
                logger.info("attempting_reconnection",
                           attempt=attempt + 1,
                           delay=delay)
                
                await asyncio.sleep(delay)
                await self._connect_func()
                
                logger.info("reconnection_successful",
                           attempt=attempt + 1)
                return
                
            except Exception as e:
                error_counter.inc()
                logger.warning("reconnection_attempt_failed",
                             attempt=attempt + 1,
                             error=str(e))
                continue

        error_counter.inc()
        logger.error("reconnection_failed",
                    max_retries=self._max_retries) 