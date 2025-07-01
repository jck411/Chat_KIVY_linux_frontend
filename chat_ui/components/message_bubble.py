"""Message bubble component for chat messages.

Renders individual chat message bubbles with user/AI styling and text updates.
"""

from kivy.metrics import dp
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from chat_ui.theme import Colors, Layout, Sizes, Spacing


class MessageBubble(MDCard):
    """Chat message bubble with optimized styling.
    
    Features:
    - User/AI message differentiation
    - Dynamic text updates for streaming
    - Optimized styling with Material Design
    """

    def __init__(self, text, is_user=False, **kwargs) -> None:
        """Initialize message bubble.
        
        Args:
            text: Message text content
            is_user: Whether this is a user message (vs AI message)
            **kwargs: Additional widget arguments
        """
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

    def update_text(self, text: str) -> None:
        """Update bubble text content.
        
        Args:
            text: New text content for the bubble
        """
        self.label.text = text

    def get_text(self) -> str:
        """Get current bubble text content.
        
        Returns:
            Current text content
        """
        return self.label.text

    def append_text(self, additional_text: str) -> None:
        """Append text to existing content (useful for streaming).
        
        Args:
            additional_text: Text to append to current content
        """
        current_text = self.label.text
        self.update_text(current_text + additional_text) 