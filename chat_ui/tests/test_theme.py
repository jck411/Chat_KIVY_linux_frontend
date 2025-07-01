"""Tests for the theme module."""
from kivy.metrics import dp

from chat_ui.theme import Colors, Layout, Sizes, Spacing


def test_colors_hex_to_list() -> None:
    """Test the hex_to_list conversion method."""
    # Test with primary blue color
    rgba_list = Colors.hex_to_list(Colors.PRIMARY_BLUE_HEX)
    assert len(rgba_list) == 4
    # Compare with small tolerance for floating point differences
    assert all(abs(a - b) < 0.01 for a, b in zip(rgba_list, Colors.PRIMARY_BLUE))

    # Test with white color
    rgba_list = Colors.hex_to_list(Colors.WHITE_HEX)
    assert len(rgba_list) == 4
    assert all(abs(a - b) < 0.01 for a, b in zip(rgba_list, Colors.WHITE))


def test_colors_constants() -> None:
    """Test that color constants are properly formatted."""
    # Test RGBA list format
    assert len(Colors.PRIMARY_BLUE) == 4
    assert all(isinstance(x, (int, float)) for x in Colors.PRIMARY_BLUE)
    assert all(0 <= x <= 1 for x in Colors.PRIMARY_BLUE)

    # Test hex format
    assert Colors.PRIMARY_BLUE_HEX.startswith("#")
    assert len(Colors.PRIMARY_BLUE_HEX) == 7


def test_sizes_dp_conversion() -> None:
    """Test that size constants are converted to dp units."""
    assert isinstance(Sizes.BUBBLE_RADIUS, float)  # dp returns float
    assert dp(20) == Sizes.BUBBLE_RADIUS
    assert dp(60) == Sizes.HEADER_HEIGHT

    # Test font sizes are strings with 'sp' unit
    assert isinstance(Sizes.TITLE_FONT, str)
    assert Sizes.TITLE_FONT.endswith("sp")


def test_spacing_dp_conversion() -> None:
    """Test that spacing constants are converted to dp units."""
    assert isinstance(Spacing.SMALL, float)
    assert dp(12) == Spacing.SMALL
    assert dp(16) == Spacing.MEDIUM
    assert dp(20) == Spacing.LARGE


def test_layout_constants() -> None:
    """Test layout constants for proper types and ranges."""
    # Test bubble width ratios
    assert isinstance(Layout.USER_BUBBLE_WIDTH, float)
    assert 0 < Layout.USER_BUBBLE_WIDTH <= 1
    assert 0 < Layout.AI_BUBBLE_WIDTH <= 1

    # Test position dictionaries
    assert isinstance(Layout.USER_BUBBLE_POS, dict)
    assert "right" in Layout.USER_BUBBLE_POS
    assert isinstance(Layout.AI_BUBBLE_POS, dict)
    assert "x" in Layout.AI_BUBBLE_POS

    # Test scroll bar width
    assert dp(4) == Layout.SCROLL_BAR_WIDTH
