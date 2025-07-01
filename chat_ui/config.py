"""
Configuration management for the chat UI
"""
import os


class Config:
    """Centralized configuration with environment variable support"""
    
    # Network settings
    WEBSOCKET_URI = os.getenv("CHAT_WEBSOCKET_URI", "ws://192.168.1.223:8000/ws/chat")
    CONNECTION_TIMEOUT = float(os.getenv("CHAT_CONNECTION_TIMEOUT", "30.0"))
    CONNECTION_TEST_TIMEOUT = float(os.getenv("CHAT_TEST_TIMEOUT", "5.0"))
    MAX_RETRIES = int(os.getenv("CHAT_MAX_RETRIES", "3"))
    RETRY_DELAY = float(os.getenv("CHAT_RETRY_DELAY", "1.0"))
    
    # Persistent connection settings - optimized for production
    PING_INTERVAL = int(os.getenv("CHAT_PING_INTERVAL", "120"))  # 2 minutes - more reasonable
    CONNECTION_HEALTH_CHECK = bool(os.getenv("CHAT_HEALTH_CHECK", "true").lower() == "true")
    HEALTH_CHECK_TIMEOUT = int(os.getenv("CHAT_HEALTH_TIMEOUT", "240"))  # 4 minutes before considering stale
    
    # Performance settings
    SCROLL_THROTTLE_MS = int(os.getenv("CHAT_SCROLL_THROTTLE_MS", "100"))
    TEXT_BATCH_MS = int(os.getenv("CHAT_TEXT_BATCH_MS", "50"))
    MAX_MESSAGE_HISTORY = int(os.getenv("CHAT_MAX_MESSAGES", "100"))
    
    # UI settings
    APP_TITLE = os.getenv("CHAT_APP_TITLE", "💬 Simple Chat")
    AI_NAME = os.getenv("CHAT_AI_NAME", "AI Assistant")
    WELCOME_MESSAGE = os.getenv("CHAT_WELCOME_MESSAGE", "👋 Hello! I'm your AI assistant. How can I help you?")
    
    # Window settings
    WINDOW_WIDTH = int(os.getenv("CHAT_WINDOW_WIDTH", "400"))
    WINDOW_HEIGHT = int(os.getenv("CHAT_WINDOW_HEIGHT", "600"))
    MIN_WIDTH = int(os.getenv("CHAT_MIN_WIDTH", "350"))
    MIN_HEIGHT = int(os.getenv("CHAT_MIN_HEIGHT", "500"))


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