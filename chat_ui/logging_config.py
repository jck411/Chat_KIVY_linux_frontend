"""Structured logging configuration for the chat UI application.
Provides consistent JSON logging across all modules.
"""

import logging
import sys
import time
from typing import Any, Dict

import structlog
from prometheus_client import Counter, Histogram, start_http_server

# Prometheus metrics
message_counter = Counter('chat_messages_total', 'Total messages processed')
message_latency = Histogram('message_processing_seconds', 'Message processing time')
error_counter = Counter('chat_errors_total', 'Total errors encountered')
websocket_state = Counter('websocket_state_changes', 'WebSocket connection state changes')

# Start metrics server on port 8000
start_http_server(8000)

# Configure standard logging to work with structlog
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

def add_timestamp(_, __, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add ISO timestamp and elapsed time to log events."""
    event_dict["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    # Add elapsed_ms since process start
    event_dict["elapsed_ms"] = int((time.time() - _process_start) * 1000)
    return event_dict

def add_module_context(logger: str, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add module name and method context to log events."""
    event_dict["module"] = logger
    event_dict["function"] = method_name
    return event_dict

# Store process start time for elapsed_ms calculation
_process_start = time.time()

# Configure structlog as the primary logging system
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_timestamp,
        add_module_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance for the given name.

    Args:
    ----
        name: The name of the module/component requesting the logger

    Returns:
    -------
        A configured structured logger instance

    """
    return structlog.get_logger(name)
