"""Tests for the configuration management critical functionality."""
import os
import sys
import pytest
import importlib

@pytest.fixture(autouse=True)
def reload_config():
    """Fixture to reload config module before each test."""
    # Clean up any existing test environment variables
    for key in list(os.environ.keys()):
        if key.startswith("CHAT_"):
            del os.environ[key]
    
    # Remove the module if it's already loaded
    if "chat_ui.config" in sys.modules:
        del sys.modules["chat_ui.config"]
    
    yield
    
    # Clean up test environment variables after each test
    for key in list(os.environ.keys()):
        if key.startswith("CHAT_"):
            del os.environ[key]
    
    # Remove the module after the test
    if "chat_ui.config" in sys.modules:
        del sys.modules["chat_ui.config"]

@pytest.fixture
def env_vars():
    """Fixture to manage environment variables."""
    original = {}
    to_set = {
        "CHAT_WEBSOCKET_URI": "ws://test:8000",
        "CHAT_CONNECTION_TIMEOUT": "15.0",
        "CHAT_MAX_RETRIES": "5",
        "CHAT_PING_INTERVAL": "60"
    }
    
    # Store original values
    for key in to_set:
        if key in os.environ:
            original[key] = os.environ[key]
    
    # Set test values
    for key, value in to_set.items():
        os.environ[key] = value
        
    yield to_set
    
    # Restore original values
    for key in to_set:
        if key in original:
            os.environ[key] = original[key]
        else:
            del os.environ[key]

def test_network_settings(env_vars):
    """Test critical path: Network configuration loading."""
    from chat_ui.config import Config
    assert Config.WEBSOCKET_URI == "ws://test:8000"
    assert Config.CONNECTION_TIMEOUT == 15.0
    assert Config.MAX_RETRIES == 5

def test_connection_health_settings(env_vars):
    """Test critical path: Connection health configuration."""
    from chat_ui.config import Config
    assert Config.PING_INTERVAL == 60
    assert Config.CONNECTION_HEALTH_CHECK is True  # Default value
    assert Config.HEALTH_CHECK_TIMEOUT == 240  # Default value

def test_performance_settings():
    """Test critical path: Performance configuration."""
    from chat_ui.config import Config
    assert Config.SCROLL_THROTTLE_MS > 0
    assert Config.TEXT_BATCH_MS > 0
    assert Config.MAX_MESSAGE_HISTORY > 0

def test_default_values():
    """Test critical path: Default value handling."""
    # Remove test environment variables
    if "CHAT_TEST_TIMEOUT" in os.environ:
        del os.environ["CHAT_TEST_TIMEOUT"]
    
    from chat_ui.config import Config
    # Should use default value
    assert Config.CONNECTION_TEST_TIMEOUT == 5.0

def test_type_conversion():
    """Test critical path: Environment variable type conversion."""
    os.environ["CHAT_MAX_RETRIES"] = "invalid"
    from chat_ui.config import Config
    # Should use default value when conversion fails
    assert Config.MAX_RETRIES == 3  # Default value

def test_boolean_conversion():
    """Test critical path: Boolean configuration handling."""
    test_cases = [
        ("true", True),
        ("True", True),
        ("false", False),
        ("False", False),
        ("invalid", True)  # Default value
    ]
    
    for input_value, expected in test_cases:
        os.environ["CHAT_HEALTH_CHECK"] = input_value
        # Remove the module to force a fresh import
        if "chat_ui.config" in sys.modules:
            del sys.modules["chat_ui.config"]
        from chat_ui.config import Config
        assert Config.CONNECTION_HEALTH_CHECK == expected 