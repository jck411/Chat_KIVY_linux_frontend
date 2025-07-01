#!/usr/bin/env python3
"""KivyMD Chat UI - Production-ready chat interface
Entry point for the application.
"""

import os
import sys
import warnings

from kivy.config import Config as KivyConfig
from kivymd.app import MDApp

from chat_ui.config import Config
from chat_ui.logging_config import get_logger

# Set up structured logger for this module
logger = get_logger(__name__)

# Configure environment variables before any Kivy imports
os.environ["KIVY_NO_CONSOLELOG"] = "1"  # Reduce console logging
os.environ["KIVY_LOG_LEVEL"] = "critical"  # Only critical errors
os.environ["KIVY_NO_FILELOG"] = "1"  # Disable file logging completely
os.environ["KIVY_NO_ARGS"] = "1"  # Don't process command line arguments

# Configure logging for production use
def configure_logging() -> None:
    """Configure logging levels for clean production output."""
    # Suppress verbose WebSocket debug logs
    import logging
    logging.getLogger("websockets").setLevel(logging.ERROR)
    logging.getLogger("websockets.protocol").setLevel(logging.ERROR)
    logging.getLogger("websockets.client").setLevel(logging.ERROR)
    logging.getLogger("websockets.server").setLevel(logging.ERROR)

    # Suppress asyncio debug messages (like selector messages)
    logging.getLogger("asyncio").setLevel(logging.ERROR)

    # Suppress Kivy verbose logs completely
    logging.getLogger("kivy").setLevel(logging.ERROR)

    # Completely suppress KivyMD warnings
    warnings.simplefilter("ignore")  # Suppress ALL warnings

    # Specifically target deprecation warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning)

    # Target KivyMD specifically
    kivymd_logger = logging.getLogger("kivymd")
    kivymd_logger.setLevel(logging.CRITICAL)  # Only critical errors
    kivymd_logger.disabled = True  # Completely disable KivyMD logging

# Configure Kivy settings before importing UI modules
def configure_kivy() -> None:
    """Configure Kivy settings for optimal performance and reduced warnings."""
    logger.info("configuring_kivy_settings",
                window_width=Config.WINDOW_WIDTH,
                window_height=Config.WINDOW_HEIGHT)

    # Window settings
    KivyConfig.set("graphics", "width", str(Config.WINDOW_WIDTH))
    KivyConfig.set("graphics", "height", str(Config.WINDOW_HEIGHT))
    KivyConfig.set("graphics", "minimum_width", str(Config.MIN_WIDTH))
    KivyConfig.set("graphics", "minimum_height", str(Config.MIN_HEIGHT))

    # Performance optimizations
    KivyConfig.set("kivy", "log_level", "critical")  # Only critical errors
    KivyConfig.set("graphics", "vsync", "1")  # Enable vsync for smoother rendering
    KivyConfig.set("graphics", "multisamples", "0")  # Disable multisampling for better performance

    # Disable problematic input providers to reduce warnings
    KivyConfig.set("input", "mtdev", "")  # Disable mtdev completely
    KivyConfig.set("input", "mouse", "mouse,multitouch_on_demand")  # Simplify mouse input

    # Configure kivy to be less verbose about clipboard issues
    KivyConfig.set("kivy", "exit_on_escape", "0")  # Don't exit on escape key
    KivyConfig.set("kivy", "window_icon", "")  # Disable window icon to avoid potential issues

# Configure everything before imports
configure_logging()
configure_kivy()

import logging

# Additional Kivy logger configuration after imports
from kivy import Logger as KivyLogger

from chat_ui.chat_screen import ModernChatScreen

KivyLogger.setLevel(logging.CRITICAL)  # Completely suppress Kivy logs

class ChatApp(MDApp):
    """Production-ready KivyMD Chat Application.

    Features:
    - Material Design 3 theming
    - Optimized performance settings
    - Clean error handling
    - Structured logging throughout
    """

    def build(self):
        """Build and configure the application."""
        logger.info("building_application", theme_style="Light", primary_palette="Blue")

        # Apply modern Material Design 3 theme
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.material_style = "M3"

        try:
            return ModernChatScreen()
        except Exception as e:
            logger.exception("application_build_failed", error=str(e))
            sys.exit(1)

    def on_start(self) -> None:
        """Called when the app starts."""
        self.title = Config.APP_TITLE
        logger.info("application_started", app_title=Config.APP_TITLE)

    def on_stop(self) -> None:
        """Called when the app stops - cleanup resources."""
        logger.info("application_stopping")
        try:
            # Get the root widget and cleanup if it has a client
            if hasattr(self.root, "client"):
                # Note: asyncio cleanup would need to be handled properly in production
                pass
            logger.info("application_stopped")
        except Exception as e:
            logger.warning("cleanup_error", error=str(e))

def main() -> None:
    """Main entry point with error handling."""
    try:
        logger.info("starting_chat_application")
        ChatApp().run()
    except KeyboardInterrupt:
        logger.info("application_interrupted_by_user")
        sys.exit(0)
    except Exception as e:
        logger.exception("application_startup_failed", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
