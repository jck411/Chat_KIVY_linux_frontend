"""Modern 2025 Chat Interface - Optimized for production use."""
import threading
import time

from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFabButton
from kivymd.uix.card import MDCard
from kivymd.uix.screen import MDScreen
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField

from chat_ui.components.chat_header import ChatHeader
from chat_ui.components.message_bubble import MessageBubble
from chat_ui.config import Config, Messages
from chat_ui.logging_config import get_logger
from chat_ui.services.message_service import (
    MessageService, MessageError, MessageTooLongError,
    MessageRateLimitError, MessageFormatError, MessageServiceError
)
from chat_ui.theme import Colors, Layout, Sizes, Spacing
from chat_ui.websocket.client import WebSocketClient
from chat_ui.websocket.connection_manager import ConnectionState

# Set up structured logger for this module
logger = get_logger(__name__)


class ModernChatScreen(MDScreen):
    """Modern chat interface with streaming support and optimized performance.

    Features:
    - Real-time message streaming
    - Scroll throttling for smooth performance
    - Text batching for efficient updates
    - Memory management with message cleanup
    - Connection state monitoring
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        logger.info("initializing_chat_screen",
                   max_messages=Config.MAX_MESSAGE_HISTORY,
                   scroll_throttle_ms=Config.SCROLL_THROTTLE_MS,
                   text_batch_ms=Config.TEXT_BATCH_MS)

        self.client = WebSocketClient()
        self.backend_available = False
        self.scroll_view = None
        self.connection_monitor_task = None

        # Header component (replaces direct status_label access)
        self.header = None

        # Message service (handles all message operations)
        self.message_service = MessageService(self.client)

        # Performance optimization variables for scrolling
        self._scroll_scheduled = False
        self._pending_scroll_event = None
        self._last_scroll_time = 0
        self._scroll_throttle_delay = Config.SCROLL_THROTTLE_MS / 1000.0

        self._setup_ui()
        self._setup_message_service()
        self._initialize_connection_monitoring()

    def _setup_message_service(self) -> None:
        """Setup message service with UI callbacks."""
        self.message_service.set_ui_callbacks(
            on_bubble_created=self._create_message_bubble,
            on_bubble_updated=None,  # Not needed - bubbles handle text updates directly
            on_focus_input=self._focus_input,
            on_scroll_bottom=self._scroll_to_bottom,
            on_cleanup_messages=self._cleanup_old_messages
        )

    def _initialize_connection_monitoring(self) -> None:
        """Initialize connection testing and monitoring."""
        logger.info("initializing_connection_monitoring", test_delay=1.0, monitor_interval=2.0)
        Clock.schedule_once(self._test_backend, 1.0)
        self.connection_monitor_task = Clock.schedule_interval(self._monitor_connection_state, 2.0)

    def _setup_ui(self) -> None:
        """Setup the main UI layout and components."""
        logger.info("setting_up_ui", theme_style="Material Design 3")
        layout = MDBoxLayout(
            orientation="vertical",
            theme_bg_color="Custom",  # Required for KivyMD 2.0+
            md_bg_color=Colors.BACKGROUND,
        )

        # Header component (new approach)
        self.header = ChatHeader()

        # Messages container with scrolling
        self.messages = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=Spacing.MEDIUM,
            padding=[Spacing.LARGE, Spacing.LARGE],
        )

        self.scroll_view = MDScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            scroll_type=["bars", "content"],
            bar_width=Layout.SCROLL_BAR_WIDTH,
        )
        self.scroll_view.add_widget(self.messages)

        # Input area
        input_card = self._create_input_area()

        # Add welcome message
        welcome = MessageBubble(Config.WELCOME_MESSAGE)
        self.messages.add_widget(welcome)

        # Assemble layout
        layout.add_widget(self.header)
        layout.add_widget(self.scroll_view)
        layout.add_widget(input_card)
        self.add_widget(layout)

        # Initial scroll to bottom
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(force=True), 0.01)



    def _create_input_area(self):
        """Create the input area with text field and send button."""
        input_card = MDCard(
            theme_bg_color="Custom",  # Required for KivyMD 2.0+
            md_bg_color=Colors.WHITE,
            elevation=3,
            radius=[0],
            size_hint_y=None,
            height=Sizes.INPUT_HEIGHT,
            padding=[Spacing.LARGE, Spacing.MEDIUM],
        )

        input_box = MDBoxLayout(
            orientation="horizontal",
            spacing=Spacing.SMALL,
        )

        self.text_input = MDTextField(
            hint_text="Type your message...",
            mode="outlined",
            font_size=Sizes.MESSAGE_FONT,
            size_hint_y=None,
            height=Sizes.BUTTON_SIZE,
            radius=[dp(24)],
            on_text_validate=self.send_message,
        )

        self.send_btn = MDFabButton(
            icon="send",
            theme_bg_color="Custom",  # Required for KivyMD 2.0+
            md_bg_color=Colors.PRIMARY_BLUE,
            size_hint=(None, None),
            size=(Sizes.BUTTON_SIZE, Sizes.BUTTON_SIZE),
            on_release=self.send_message,
        )

        input_box.add_widget(self.text_input)
        input_box.add_widget(self.send_btn)
        input_card.add_widget(input_box)

        return input_card

    def _scroll_to_bottom(self, force=False) -> None:
        """Scroll to bottom with throttling for better performance."""
        current_time = time.time()

        if force or (current_time - self._last_scroll_time) >= self._scroll_throttle_delay:
            self._do_scroll()
            self._last_scroll_time = current_time

            # Cancel any pending scroll
            if self._pending_scroll_event:
                self._pending_scroll_event.cancel()
                self._pending_scroll_event = None
            self._scroll_scheduled = False

        elif not self._scroll_scheduled:
            self._scroll_scheduled = True
            remaining_delay = (self._scroll_throttle_delay -
                              (current_time - self._last_scroll_time))
            self._pending_scroll_event = Clock.schedule_once(
                self._do_throttled_scroll, remaining_delay)

    def _do_scroll(self) -> None:
        """Perform the actual scroll operation."""
        self.scroll_view.scroll_y = 0

    def _do_throttled_scroll(self, dt) -> None:
        """Perform scheduled throttled scroll."""
        self._do_scroll()
        self._last_scroll_time = time.time()
        self._scroll_scheduled = False
        self._pending_scroll_event = None

    def _test_backend(self, dt) -> None:
        """Test backend connection in background thread."""
        thread = threading.Thread(target=self._threaded_test, daemon=True)
        thread.start()

    def _threaded_test(self) -> None:
        """Test connection availability."""
        try:
            connected = self.client.test_connection_sync()
            self.backend_available = connected

            status_text = Messages.ONLINE if connected else Messages.DEMO_MODE
            logger.info("backend_connection_test", connected=connected, status=status_text)
            Clock.schedule_once(lambda dt: self.header.update_status(status_text))
        except Exception as e:
            logger.warning("backend_connection_test_failed", error=str(e))
            Clock.schedule_once(lambda dt: self.header.update_status(Messages.DEMO_MODE))

    def _monitor_connection_state(self, dt) -> None:
        """Monitor and update UI based on connection state."""
        try:
            state = self.client.get_connection_state()

            if state == ConnectionState.CONNECTED:
                if not self.backend_available:
                    self.backend_available = True
                    self.header.update_status(Messages.ONLINE)
                    logger.info("connection_state_changed", state="connected", backend_available=True)
            elif state == ConnectionState.CONNECTING:
                self.header.update_status(Messages.CONNECTING)
                logger.info("connection_state_changed", state="connecting")
            elif state == ConnectionState.RECONNECTING:
                self.header.update_status(Messages.RECONNECTING)
                logger.info("connection_state_changed", state="reconnecting")
            elif state == ConnectionState.FAILED:
                self.backend_available = False
                self.header.update_status(Messages.CONNECTION_FAILED)
                logger.warning("connection_state_changed",
                               state="failed", backend_available=False)
            elif state == ConnectionState.DISCONNECTED:
                self.backend_available = False
                self.header.update_status(Messages.DEMO_MODE)
                logger.info("connection_state_changed", state="disconnected", mode="demo")

        except Exception as e:
            # Fallback to demo mode
            logger.exception("connection_monitoring_error", error=str(e))
            self.backend_available = False
            self.header.update_status(Messages.DEMO_MODE)

    def send_message(self, instance) -> None:
        """Handle message sending - now delegates to MessageService."""
        text = self.text_input.text.strip()
        if not text:
            return

        try:
            # Add user message bubble
            user_bubble = MessageBubble(text, is_user=True)
            self.messages.add_widget(user_bubble)
            self.text_input.text = ""

            # Reset message service state
            self.message_service.reset_current_bubble()

            # Delegate to message service
            self.message_service.send_message(
                text=text,
                backend_available=self.backend_available,
                total_messages=len(self.messages.children)
            )
        except MessageTooLongError as e:
            self._show_error_message(f"❌ {str(e)}")
        except MessageRateLimitError as e:
            self._show_error_message(f"⚠️ {str(e)}")
        except MessageFormatError as e:
            self._show_error_message(f"❌ {str(e)}")
        except MessageServiceError as e:
            self._show_error_message(f"❌ Service Error: {str(e)}")
        except Exception as e:
            logger.exception("unexpected_error", error=str(e))
            self._show_error_message("❌ An unexpected error occurred. Please try again.")

    def _show_error_message(self, error_text: str) -> None:
        """Show error message in chat.
        
        Args:
            error_text: Error message to display
        """
        error_bubble = MessageBubble(error_text, is_user=False)
        self.messages.add_widget(error_bubble)
        self._scroll_to_bottom(force=True)

    # UI Callback methods for MessageService
    def _create_message_bubble(self, text: str, is_user: bool = False) -> MessageBubble:
        """Create and add a message bubble to the UI.
        
        Args:
            text: Message text
            is_user: Whether this is a user message
            
        Returns:
            Created bubble widget
        """
        bubble = MessageBubble(text, is_user=is_user)
        self.messages.add_widget(bubble)
        return bubble

    def _focus_input(self) -> None:
        """Focus the text input field."""
        self.text_input.focus = True

    def _cleanup_old_messages(self) -> None:
        """Remove old messages to prevent memory bloat during long conversations."""
        messages_to_remove = self.message_service.cleanup_old_messages(len(self.messages.children))
        for _ in range(messages_to_remove):
            oldest_message = self.messages.children[-1]
            self.messages.remove_widget(oldest_message)


