#!/usr/bin/env python3
"""
KivyMD Chat UI - Production-ready chat interface
Entry point for the application
"""

import logging
import warnings
import sys
import os
from kivy.config import Config as KivyConfig
from kivymd.app import MDApp

from chat_ui.config import Config

# Configure environment variables before any Kivy imports
os.environ['KIVY_NO_CONSOLELOG'] = '1'  # Reduce console logging
os.environ['KIVY_LOG_LEVEL'] = 'critical'  # Only critical errors
os.environ['KIVY_NO_FILELOG'] = '1'  # Disable file logging completely
os.environ['KIVY_NO_ARGS'] = '1'  # Don't process command line arguments

# Configure logging for production use
def configure_logging():
    """Configure logging levels for clean production output"""
    # Set root logger to WARNING level to reduce verbosity
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    
    # Suppress verbose WebSocket debug logs
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
def configure_kivy():
    """Configure Kivy settings for optimal performance and reduced warnings"""
    # Window settings
    KivyConfig.set('graphics', 'width', str(Config.WINDOW_WIDTH))
    KivyConfig.set('graphics', 'height', str(Config.WINDOW_HEIGHT))
    KivyConfig.set('graphics', 'minimum_width', str(Config.MIN_WIDTH))
    KivyConfig.set('graphics', 'minimum_height', str(Config.MIN_HEIGHT))
    
    # Performance optimizations
    KivyConfig.set('kivy', 'log_level', 'critical')  # Only critical errors
    KivyConfig.set('graphics', 'vsync', '1')  # Enable vsync for smoother rendering
    KivyConfig.set('graphics', 'multisamples', '0')  # Disable multisampling for better performance
    
    # Disable problematic input providers to reduce warnings
    KivyConfig.set('input', 'mtdev', '')  # Disable mtdev completely
    KivyConfig.set('input', 'mouse', 'mouse,multitouch_on_demand')  # Simplify mouse input
    
    # Configure kivy to be less verbose about clipboard issues
    KivyConfig.set('kivy', 'exit_on_escape', '0')  # Don't exit on escape key
    KivyConfig.set('kivy', 'window_icon', '')  # Disable window icon to avoid potential issues

# Configure everything before imports
configure_logging()
configure_kivy()

from chat_ui.modern_chat import ModernChatScreen

# Additional Kivy logger configuration after imports
from kivy import Logger as KivyLogger
KivyLogger.setLevel(logging.CRITICAL)  # Completely suppress Kivy logs


class ChatApp(MDApp):
    """
    Production-ready KivyMD Chat Application
    
    Features:
    - Material Design 3 theming
    - Optimized performance settings
    - Clean error handling
    - Minimal logging output
    """
    
    def build(self):
        """Build and configure the application"""
        # Apply modern Material Design 3 theme
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.material_style = "M3"
        
        try:
            return ModernChatScreen()
        except Exception as e:
            print(f"Failed to initialize chat interface: {e}")
            sys.exit(1)
    
    def on_start(self):
        """Called when the app starts"""
        self.title = Config.APP_TITLE
        print(f"🚀 {Config.APP_TITLE} started successfully")
    
    def on_stop(self):
        """Called when the app stops - cleanup resources"""
        try:
            # Get the root widget and cleanup if it has a client
            if hasattr(self.root, 'client'):
                # Note: asyncio cleanup would need to be handled properly in production
                pass
        except Exception:
            pass  # Ignore cleanup errors


def main():
    """Main entry point with error handling"""
    try:
        ChatApp().run()
    except KeyboardInterrupt:
        print("\n👋 Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Application failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 