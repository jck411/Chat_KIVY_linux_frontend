"""Modern 2025 Chat Interface - Optimized for production use."""
import threading
import time

from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFabButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField

from chat_ui.config import Config, Messages
from chat_ui.logging_config import get_logger
from chat_ui.theme import Colors, Layout, Sizes, Spacing
from chat_ui.websocket_client import ChatWebSocketClient, ConnectionState

# Set up structured logger for this module
logger = get_logger(__name__)


class ModernBubble(MDCard):
    """Chat message bubble with optimized styling."""

    def __init__(self, text, is_user=False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.elevation = 0 if is_user else 1
        self.radius = [Sizes.BUBBLE_RADIUS]
        self.size_hint_y = None
        self.adaptive_height = True
        self.padding = [Spacing.MEDIUM, Spacing.SMALL]

        if is_user:
            self.theme_bg_color = "Custom"  # Required for KivyMD 2.0+
            self.md_bg_color = Colors.PRIMARY_BLUE
            self.pos_hint = Layout.USER_BUBBLE_POS
            self.size_hint_x = Layout.USER_BUBBLE_WIDTH
            text_color = Colors.TEXT_LIGHT
        else:
            self.theme_bg_color = "Custom"  # Required for KivyMD 2.0+
            self.md_bg_color = Colors.LIGHT_GRAY
            self.pos_hint = Layout.AI_BUBBLE_POS
            self.size_hint_x = Layout.AI_BUBBLE_WIDTH
            text_color = Colors.TEXT_DARK

        self.label = MDLabel(
            text=text,
            theme_text_color="Custom",
            text_color=text_color,
            font_size=Sizes.MESSAGE_FONT,
            adaptive_height=True,
            text_size=(dp(300), None),
            markup=True,
        )
        self.add_widget(self.label)

    def update_text(self, text) -> None:
        """Update bubble text content."""
        self.label.text = text


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

        self.client = ChatWebSocketClient()
        self.current_bubble = None
        self.backend_available = False
        self.scroll_view = None
        self.connection_monitor_task = None

        # Performance optimization variables
        self._scroll_scheduled = False
        self._pending_scroll_event = None
        self._last_scroll_time = 0
        self._scroll_throttle_delay = Config.SCROLL_THROTTLE_MS / 1000.0

        # Text batching for streaming optimization
        self._pending_chunks = []
        self._text_update_scheduled = False
        self._text_batch_delay = Config.TEXT_BATCH_MS / 1000.0

        # Memory management
        self.max_messages = Config.MAX_MESSAGE_HISTORY

        self._setup_ui()
        self._initialize_connection_monitoring()

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

        # Header with status
        header = self._create_header()

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
        welcome = ModernBubble(Config.WELCOME_MESSAGE)
        self.messages.add_widget(welcome)

        # Assemble layout
        layout.add_widget(header)
        layout.add_widget(self.scroll_view)
        layout.add_widget(input_card)
        self.add_widget(layout)

        # Initial scroll to bottom
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(force=True), 0.01)

    def _create_header(self):
        """Create the header with avatar and status."""
        header = MDCard(
            theme_bg_color="Custom",  # Required for KivyMD 2.0+
            md_bg_color=Colors.WHITE,
            elevation=2,
            radius=[0],
            size_hint_y=None,
            height=Sizes.HEADER_HEIGHT,
            padding=Spacing.MEDIUM,
        )

        header_content = MDBoxLayout(
            orientation="horizontal",
            spacing=Spacing.SMALL,
        )

        # Avatar
        avatar = MDCard(
            theme_bg_color="Custom",  # Required for KivyMD 2.0+
            md_bg_color=Colors.PRIMARY_BLUE,
            size_hint=(None, None),
            size=(Sizes.AVATAR_SIZE, Sizes.AVATAR_SIZE),
            radius=[Sizes.BUBBLE_RADIUS],
        )

        # Title and status
        title_box = MDBoxLayout(orientation="vertical")

        title = MDLabel(
            text=Config.AI_NAME,
            font_size=Sizes.TITLE_FONT,
            bold=True,
            size_hint_y=None,
            height=dp(24),
        )

        self.status_label = MDLabel(
            text=Messages.CONNECTING,
            font_size=Sizes.STATUS_FONT,
            theme_text_color="Custom",
            text_color=Colors.TEXT_MUTED,
            size_hint_y=None,
            height=dp(18),
        )

        title_box.add_widget(title)
        title_box.add_widget(self.status_label)
        header_content.add_widget(avatar)
        header_content.add_widget(title_box)
        header.add_widget(header_content)

        return header

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
            Clock.schedule_once(lambda dt: setattr(self.status_label, "text", status_text))
        except Exception as e:
            logger.warning("backend_connection_test_failed", error=str(e))
            Clock.schedule_once(lambda dt: setattr(self.status_label, "text", Messages.DEMO_MODE))

    def _monitor_connection_state(self, dt) -> None:
        """Monitor and update UI based on connection state."""
        try:
            state = self.client.get_connection_state()

            if state == ConnectionState.CONNECTED:
                if not self.backend_available:
                    self.backend_available = True
                    self.status_label.text = Messages.ONLINE
                    logger.info("connection_state_changed", state="connected", backend_available=True)
            elif state == ConnectionState.CONNECTING:
                self.status_label.text = Messages.CONNECTING
                logger.info("connection_state_changed", state="connecting")
            elif state == ConnectionState.RECONNECTING:
                self.status_label.text = Messages.RECONNECTING
                logger.info("connection_state_changed", state="reconnecting")
            elif state == ConnectionState.FAILED:
                self.backend_available = False
                self.status_label.text = Messages.CONNECTION_FAILED
                logger.warning("connection_state_changed",
                               state="failed", backend_available=False)
            elif state == ConnectionState.DISCONNECTED:
                self.backend_available = False
                self.status_label.text = Messages.DEMO_MODE
                logger.info("connection_state_changed", state="disconnected", mode="demo")

        except Exception as e:
            # Fallback to demo mode
            logger.exception("connection_monitoring_error", error=str(e))
            self.backend_available = False
            self.status_label.text = Messages.DEMO_MODE

    def send_message(self, instance) -> None:
        """Handle message sending with backend or demo mode."""
        text = self.text_input.text.strip()
        if not text:
            return

        logger.info("sending_message",
                   message_length=len(text),
                   backend_available=self.backend_available,
                   total_messages=len(self.messages.children))

        # Add user message
        user_bubble = ModernBubble(text, is_user=True)
        self.messages.add_widget(user_bubble)
        self.text_input.text = ""
        self._cleanup_old_messages()
        self._scroll_to_bottom(force=True)

        # Reset current bubble for new response
        self.current_bubble = None

        if self.backend_available:
            self._send_to_backend(text)
        else:
            self._show_demo_response(text)

    def _send_to_backend(self, message) -> None:
        """Send message to backend in background thread."""
        thread = threading.Thread(target=self._threaded_send, args=(message,), daemon=True)
        thread.start()

    def _show_demo_response(self, message) -> None:
        """Show demo response when backend is unavailable."""
        logger.info("showing_demo_response", original_message_length=len(message))
        demo_bubble = ModernBubble(Messages.DEMO_RESPONSE.format(message=message))
        self.messages.add_widget(demo_bubble)
        self._scroll_to_bottom(force=True)
        Clock.schedule_once(lambda dt: self._focus_input(), 0.5)

    def _threaded_send(self, message) -> None:
        """Send message to backend with error handling."""
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

    def _show_error_message(self, error_msg) -> None:
        """Show error message on main thread."""
        try:
            logger.warning("displaying_error_message", error=error_msg)
            error_bubble = ModernBubble(f"❌ {error_msg}")
            self.messages.add_widget(error_bubble)
            self._scroll_to_bottom(force=True)
            self._focus_input()
        except Exception as e:
            # Fallback to status update
            logger.exception("error_display_failed", error=str(e), original_error=error_msg)
            self.status_label.text = f"❌ {error_msg[:30]}..."

    def _format_error_message(self, error: str) -> str:
        """Format error messages to be user-friendly."""
        error_lower = error.lower()
        if "timeout" in error_lower:
            return Messages.TIMEOUT
        elif "connection refused" in error_lower:
            return Messages.CONNECTION_REFUSED
        elif "failed after" in error_lower:
            return Messages.MAX_RETRIES
        else:
            return Messages.UNKNOWN_ERROR.format(error=error)

    def _on_chunk(self, chunk) -> None:
        """Handle incoming chunk with batching for better performance."""
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
        self.text_input.focus = True

    def _cleanup_old_messages(self) -> None:
        """Remove old messages to prevent memory bloat during long conversations."""
        if len(self.messages.children) > self.max_messages:
            messages_to_remove = len(self.messages.children) - self.max_messages
            logger.info("cleaning_up_old_messages",
                       total_messages=len(self.messages.children),
                       removing_count=messages_to_remove,
                       max_allowed=self.max_messages)
            for _ in range(messages_to_remove):
                oldest_message = self.messages.children[-1]
                self.messages.remove_widget(oldest_message)

    def _append_chunk_batch(self, text) -> None:
        """Append batched text to the current bubble with optimized scrolling."""
        # Create bubble on first chunk
        if not self.current_bubble:
            self.current_bubble = ModernBubble(text)
            self.messages.add_widget(self.current_bubble)
            self._scroll_to_bottom(force=True)
        else:
            # Append to existing bubble
            current_text = self.current_bubble.label.text
            self.current_bubble.update_text(current_text + text)
            self._scroll_to_bottom()
