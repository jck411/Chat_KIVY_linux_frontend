"""Chat header component with avatar, status, and expandable menu system.

This component manages the expandable chat header with avatar, status, icons, and menu system.
Future expansion will include toolbar, user profile dropdown, theme switcher, etc.
"""

from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from chat_ui.config import Config, Messages
from chat_ui.logging_config import get_logger
from chat_ui.theme import Colors, Layout, Sizes, Spacing

# Set up structured logger for this module
logger = get_logger(__name__)


class ChatHeader(MDCard):
    """Expandable chat header with avatar, status, and future menu capabilities.
    
    Features:
    - Avatar display
    - AI name and connection status
    - Ready for expansion with icons, menu bar, settings
    - Clean interface for status updates
    """

    def __init__(self, **kwargs) -> None:
        """Initialize the chat header component."""
        super().__init__(**kwargs)
        logger.info("initializing_chat_header", ai_name=Config.AI_NAME)
        
        # Configure the header card
        self.theme_bg_color = "Custom"  # Required for KivyMD 2.0+
        self.md_bg_color = Colors.WHITE
        self.elevation = 2
        self.radius = [0]
        self.size_hint_y = None
        self.height = Sizes.HEADER_HEIGHT
        self.padding = Spacing.MEDIUM

        # Create header components
        self._create_header_content()

    def _create_header_content(self) -> None:
        """Create the main header content with avatar and status."""
        header_content = MDBoxLayout(
            orientation="horizontal",
            spacing=Spacing.SMALL,
        )

        # Avatar
        avatar = self._create_avatar()
        
        # Title and status area
        title_box = self._create_title_status_area()

        # Future: Add menu/icon area here
        # menu_area = self._create_menu_area()

        header_content.add_widget(avatar)
        header_content.add_widget(title_box)
        # header_content.add_widget(menu_area)  # Future expansion
        
        self.add_widget(header_content)

    def _create_avatar(self) -> MDCard:
        """Create the avatar component."""
        avatar = MDCard(
            theme_bg_color="Custom",  # Required for KivyMD 2.0+
            md_bg_color=Colors.PRIMARY_BLUE,
            size_hint=(None, None),
            size=(Sizes.AVATAR_SIZE, Sizes.AVATAR_SIZE),
            radius=[Sizes.BUBBLE_RADIUS],
        )
        return avatar

    def _create_title_status_area(self) -> MDBoxLayout:
        """Create the title and status display area."""
        title_box = MDBoxLayout(orientation="vertical")

        # AI name title
        title = MDLabel(
            text=Config.AI_NAME,
            font_size=Sizes.TITLE_FONT,
            bold=True,
            size_hint_y=None,
            height=dp(24),
        )

        # Status label (accessible from outside)
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
        
        return title_box

    def update_status(self, status_text: str) -> None:
        """Update the connection status display.
        
        Args:
            status_text: The status message to display
        """
        logger.info("updating_header_status", new_status=status_text)
        self.status_label.text = status_text

    def get_status(self) -> str:
        """Get the current status text.
        
        Returns:
            Current status text
        """
        return self.status_label.text

    # Future expansion methods (ready for implementation):
    
    def _create_menu_area(self) -> MDBoxLayout:
        """Create the menu/icon area (future expansion)."""
        # This will contain:
        # - Settings icon
        # - Theme switcher
        # - Menu dropdown
        # - Profile options
        pass

    def add_menu_item(self, icon: str, callback, tooltip: str = "") -> None:
        """Add a menu item to the header (future expansion)."""
        pass

    def set_theme_mode(self, dark_mode: bool) -> None:
        """Toggle between light and dark themes (future expansion)."""
        pass 