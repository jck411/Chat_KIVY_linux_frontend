"""
Configuration management for the chat UI
"""
import os
from typing import Any, TypeVar, Callable, Optional, Union

T = TypeVar('T')

def safe_convert(value: Optional[str], convert_fn: Callable[[str], T], default: T) -> T:
    """Safely convert a string value to target type, returning default if conversion fails."""
    if value is None:
        return default
    try:
        return convert_fn(value)
    except (ValueError, TypeError):
        return default

def parse_bool(value: Optional[str], default: bool = True) -> bool:
    """Parse string to boolean, handling common boolean string representations."""
    if value is None:
        return default
    value = value.lower().strip()
    if value in ('true', '1', 'yes', 'on', 't', 'y'):
        return True
    if value in ('false', '0', 'no', 'off', 'f', 'n'):
        return False
    return default

class Config:
    """Centralized configuration with environment variable support"""

    # Network settings
    WEBSOCKET_URI = os.getenv("CHAT_WEBSOCKET_URI",
                                 "ws://192.168.1.223:8000/ws/chat")
    CONNECTION_TIMEOUT = safe_convert(
        os.getenv("CHAT_CONNECTION_TIMEOUT"), float, 30.0)
    CONNECTION_TEST_TIMEOUT = safe_convert(
        os.getenv("CHAT_TEST_TIMEOUT"), float, 5.0)
    MAX_RETRIES = safe_convert(
        os.getenv("CHAT_MAX_RETRIES"), int, 3)
    RETRY_DELAY = safe_convert(
        os.getenv("CHAT_RETRY_DELAY"), float, 1.0)

    # Persistent connection settings - optimized for production
    PING_INTERVAL = safe_convert(
        os.getenv("CHAT_PING_INTERVAL"), int, 120)  # 2 minutes
    CONNECTION_HEALTH_CHECK = parse_bool(
        os.getenv("CHAT_HEALTH_CHECK"), True)
    HEALTH_CHECK_TIMEOUT = safe_convert(
        os.getenv("CHAT_HEALTH_TIMEOUT"), int, 240)  # 4 minutes

    # Performance settings
    SCROLL_THROTTLE_MS = safe_convert(
        os.getenv("CHAT_SCROLL_THROTTLE_MS"), int, 100)
    TEXT_BATCH_MS = safe_convert(
        os.getenv("CHAT_TEXT_BATCH_MS"), int, 50)
    MAX_MESSAGE_HISTORY = safe_convert(
        os.getenv("CHAT_MAX_MESSAGES"), int, 100)

    # UI settings
    APP_TITLE = os.getenv("CHAT_APP_TITLE", "💬 Simple Chat")
    AI_NAME = os.getenv("CHAT_AI_NAME", "AI Assistant")
    WELCOME_MESSAGE = os.getenv("CHAT_WELCOME_MESSAGE", "👋 Hello! I'm your AI assistant. How can I help you?")

    # Window settings
    WINDOW_WIDTH = safe_convert(
        os.getenv("CHAT_WINDOW_WIDTH"), int, 400)
    WINDOW_HEIGHT = safe_convert(
        os.getenv("CHAT_WINDOW_HEIGHT"), int, 600)
    MIN_WIDTH = safe_convert(
        os.getenv("CHAT_MIN_WIDTH"), int, 350)
    MIN_HEIGHT = safe_convert(
        os.getenv("CHAT_MIN_HEIGHT"), int, 500)

# Log configuration loading (avoid circular import by doing this at the end)
def _log_config_loading():
    """Log configuration values after module is fully loaded"""
    try:
        from chat_ui.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("configuration_loaded",
                   websocket_uri=Config.WEBSOCKET_URI,
                   connection_timeout=Config.CONNECTION_TIMEOUT,
                   max_retries=Config.MAX_RETRIES,
                   window_size=f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
    except ImportError:
        # Fallback if logging not available during imports
        pass

# Call after class definition to avoid circular imports
_log_config_loading()

class Messages:
    """User-facing message templates"""

    CONNECTING = "🔄 Connecting..."
    ONLINE = "🟢 Online"
    RECONNECTING = "🔄 Reconnecting..."
    DEMO_MODE = "🔴 Demo Mode"
    CONNECTION_FAILED = "❌ Connection Failed"

    # Error messages
    TIMEOUT = "Connection timeout. Please check your network and try again."
    CONNECTION_REFUSED = "Cannot connect to server. Please make sure the backend is running."
    MAX_RETRIES = "Connection failed after multiple attempts. Please try again later."
    UNKNOWN_ERROR = "Something went wrong: {error}"

    # Demo response template
    DEMO_RESPONSE = "Thanks for saying '{message}'! 💡 I'm in demo mode - connect your backend for AI responses."
