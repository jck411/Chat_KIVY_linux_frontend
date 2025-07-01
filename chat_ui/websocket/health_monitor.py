"""Health monitoring for WebSocket connections.

This module provides health monitoring with ping/pong mechanism
and automatic reconnection on connection issues.
"""

import asyncio
import json
import time
from typing import Callable, Coroutine, Any, Optional

from chat_ui.logging_config import get_logger

# Set up structured logger for this module
logger = get_logger(__name__)

class HealthMonitor:
    """Monitors WebSocket connection health with ping/pong mechanism.
    
    Features:
    - Periodic ping/pong checks
    - Configurable health thresholds
    - Automatic unhealthy state detection
    - Clean shutdown support
    """

    def __init__(
        self,
        ping_interval: float,
        health_timeout: float,
        on_unhealthy: Callable[[], Coroutine[Any, Any, None]],
        send_message: Callable[[str], Coroutine[Any, Any, None]]
    ) -> None:
        """Initialize health monitor.
        
        Args:
            ping_interval: Seconds between ping messages
            health_timeout: Seconds to wait for pong before declaring unhealthy
            on_unhealthy: Callback when connection becomes unhealthy
            send_message: Function to send messages through websocket
        """
        self._ping_interval = ping_interval
        self._health_timeout = health_timeout
        self._on_unhealthy = on_unhealthy
        self._send_message = send_message
        self._last_ping_time = 0
        self._stop_monitor = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start health monitoring."""
        logger.info("starting_health_monitor",
                   ping_interval=self._ping_interval,
                   health_timeout=self._health_timeout)
        self._stop_monitor = False
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop health monitoring cleanly."""
        logger.info("stopping_health_monitor")
        self._stop_monitor = True
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    def update_last_ping(self) -> None:
        """Update last successful ping time."""
        self._last_ping_time = time.time()

    async def _monitor_loop(self) -> None:
        """Main monitoring loop with error handling."""
        while not self._stop_monitor:
            try:
                await asyncio.sleep(self._ping_interval)
                await self._check_health()
            except Exception as e:
                logger.exception("health_monitor_error", error=str(e))
                await asyncio.sleep(self._ping_interval)

    async def _check_health(self) -> None:
        """Check connection health status."""
        current_time = time.time()
        if current_time - self._last_ping_time > self._health_timeout:
            logger.warning("connection_unhealthy",
                         last_ping=self._last_ping_time,
                         current_time=current_time,
                         timeout=self._health_timeout)
            await self._on_unhealthy()
        else:
            try:
                ping_data = {
                    "type": "ping",
                    "timestamp": current_time
                }
                await self._send_message(json.dumps(ping_data))
            except Exception as e:
                logger.warning("ping_failed", error=str(e))
                await self._on_unhealthy() 