# Chat_KIVY_linux_frontend

A chat interface built with KivyMD for Linux environments, featuring WebSocket communication and structured logging.

## Features

- Real-time WebSocket messaging with streaming responses
- Material Design 3 UI with KivyMD
- Structured JSON logging with `structlog`
- Connection state monitoring and automatic reconnection
- Message history management
- Performance optimizations for scrolling and text updates

## Project Structure

```
├── main.py                    # App entry point
├── chat_ui/
│   ├── chat_screen.py        # Main UI screen
│   ├── components/           # UI components
│   ├── services/            # Business logic
│   ├── websocket_client.py   # WebSocket handling
│   ├── logging_config.py     # Logging setup
│   ├── theme.py             # UI styling
│   ├── config.py            # Configuration
│   └── tests/               # Test suite
└── pyproject.toml           # Package management
```

## Setup

### System Requirements
```bash
sudo apt-get install xclip xsel  # For clipboard support
```

### Installation
```bash
git clone <repo-url>
cd Chat_KIVY_linux_frontend
uv sync
```

## Usage

```bash
# Run the application
uv run python main.py

# Development mode with debug logging
KIVY_LOG_LEVEL=debug uv run python main.py
```

## Configuration

Environment variables for customization:

```bash
# Connection
CHAT_WEBSOCKET_URI="ws://localhost:8000/ws/chat"
CHAT_CONNECTION_TIMEOUT="30.0"
CHAT_MAX_RETRIES="3"

# Performance
CHAT_SCROLL_THROTTLE_MS="100"
CHAT_TEXT_BATCH_MS="50"
CHAT_MAX_MESSAGES="100"

# UI
CHAT_APP_TITLE="Chat App"
CHAT_WINDOW_SIZE="400x600"
```

## WebSocket Protocol

Messages format:
```json
// Send
{"type": "text_message", "id": "uuid", "content": "message"}

// Receive
{"type": "chunk", "content": "partial text", "id": "uuid"}
{"type": "complete", "id": "uuid"}
```

## Development

```bash
# Run tests
uv run pytest chat_ui/tests/ -v --cov=chat_ui

# Code quality
uv run ruff check --fix
uv run mypy --strict chat_ui/
```

## Tech Stack

- Python 3.13.5
- KivyMD 2.0.1
- Kivy 2.3.1
- WebSockets 13.1
- Structlog 24.1.0 