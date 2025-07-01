# Project Rules and Configuration

## ⚠️ Temporary Rule Overrides and Known Issues

### KivyMD Dependency Exception
We currently have a **temporary override** of our standard version pinning rules due to Python 3.13.5 compatibility requirements:

1. **Standard Rule**: All dependencies must follow version pinning rules:
   - Stable releases: Use caret version (`^<version>`)
   - Prereleases: Use exact version (`==<version>`)
2. **Current Override**: KivyMD is using a specific commit from master branch
3. **Reason**: No stable KivyMD version currently supports Python 3.13.5
4. **Implementation**:
   - Use specific commit hash in pyproject.toml: `rev = "a1b2c3d4"`
   - Document the commit hash in `kivymd_version.txt`
   - Test new commits before updating the hash
5. **Risks**:
   - Potential breaking changes from master branch
   - Reduced reproducibility if commit hash not specified
   - Possible compatibility issues with other dependencies
6. **Mitigation**:
   - Always use specific commit hash, never floating master
   - Regular testing of the specified commit
   - Monitoring KivyMD releases for stable Python 3.13.5 support
   - Planning to switch to stable version once available

### Timeline and Resolution
- **Current Status**: Using KivyMD from commit hash a1b2c3d4 (as of July 2025)
- **Expected Resolution**: When KivyMD 2.0.0 stable is released with Python 3.13.5 support
- **Monitoring**: Watch [KivyMD GitHub releases](https://github.com/kivymd/KivyMD/releases) for updates

### Impact on Development
1. **Build Reproducibility**: 
   - Builds may not be perfectly reproducible
   - Document the commit hash used in your development
2. **Development Process**:
   - Test thoroughly after any dependency updates
   - Report any compatibility issues to the KivyMD team
3. **New Development**:
   - Consider compatibility impact when adding new features
   - Document any workarounds needed for KivyMD master

### Package Management
- Use `uv` for all Python package management
- Never use pip, poetry, or conda directly
- No need to activate virtual environment when using `uv`
- Version pinning rules:
  - Stable releases: Use caret version (`^<version>`)
  - Prereleases (alpha, beta, RC): Use exact version (`==<version>`)
  - Document any version changes in git commits

### Installation Commands
```bash
# Remove old environment (if exists)
rm -rf .venv

# Create new environment with Python 3.13.5
uv venv --python=3.13.5

# Install dependencies in correct order
uv add "kivy==2.3.1"

# Install KivyMD from master branch for Python 3.13.5 compatibility
# IMPORTANT: Replace $COMMIT_HASH with the last known working commit
# Example: @a1b2c3d4e5f6... (get latest working hash from team)
uv add "git+https://github.com/kivymd/KivyMD.git@$COMMIT_HASH"

# After installing KivyMD, document the installed commit hash:
uv run pip freeze | grep kivymd > kivymd_version.txt

# Install other dependencies with exact versions
uv add "websockets^13.1" "structlog^24.1.0"

# Run the application
uv run python main.py
```

## System Dependencies (Linux)
The following system packages are required for Kivy to work properly:
```bash
sudo apt-get update
sudo apt-get install -y python3-dev build-essential git make autoconf automake libtool \
    pkg-config cmake ninja-build libasound2-dev libpulse-dev libaudio-dev \
    libjack-dev libsndio-dev libsamplerate0-dev libx11-dev libxext-dev \
    libxrandr-dev libxcursor-dev libxfixes-dev libxi-dev libxss-dev libwayland-dev \
    libxkbcommon-dev libdrm-dev libgbm-dev libgl1-mesa-dev libgles2-mesa-dev \
    libegl1-mesa-dev libdbus-1-dev libibus-1.0-dev libudev-dev fcitx-libs-dev xclip
```

## Important Notes
1. **KivyMD Version Management (TEMPORARY EXCEPTION)**:
   - Currently using KivyMD from a specific master branch commit
   - This is a temporary solution until stable Python 3.13.5 support
   - Document your working commit hash in `kivymd_version.txt`
   - Report any issues to the team immediately

2. **Version Pinning Rules**:
   - All dependencies MUST use exact version pins (==)
   - Exception: KivyMD (temporary, see above)
   - Never use version ranges (^, ~, >=, etc.)
   - Document any version changes in git commits

3. **Environment Management**:
   - Virtual environment is managed automatically by `uv`
   - System dependencies must be installed before Python packages
   - Keep `kivymd_version.txt` updated with your working commit

4. **Feature Support**:
   - Material Design features available in KivyMD development version
   - Some features may be unstable due to using master branch
   - Test thoroughly after any dependency updates

## Development Workflow
1. Install system dependencies first
2. Use `uv` for all Python package management
3. Run the app with `uv run python main.py`
4. Keep this document updated with any new dependencies or version changes

## Version Compatibility Matrix
| Component  | Version | Notes |
|------------|---------|-------|
| Python     | 3.13.5  | Required for latest features |
| Kivy       | 2.3.1   | Compatible with Python 3.13.5 |
| KivyMD     | master  | Development version required for Python 3.13.5 |
| WebSockets | 13.1    | Async support |
| structlog  | 24.1.0  | Logging support |

## Future Upgrade Path
1. Monitor KivyMD 2.0.0 stable release
2. Switch back to stable KivyMD version once 2.0.0 is released with Python 3.13.5 support
3. Test all functionality after any version changes
4. Update documentation accordingly

## Critical Logic Paths & Testing Requirements

The following paths are considered critical logic and require 70% test coverage:

### Core Message Handling
- `chat_ui/services/message_service.py`
  - Message sending and receiving
  - Error handling and formatting
  - Message history management
  - Text batching optimization

### WebSocket Communication
- `chat_ui/websocket_client.py`
  - Connection management
  - Message streaming
  - Reconnection logic
  - Health monitoring

### Configuration Management
- `chat_ui/config.py`
  - Environment variable handling
  - Critical system settings

Non-critical paths (standard testing applies):
- UI components (chat_ui/components/*)
- Theme and layout code
- General utilities

### Coverage Configuration
```toml
[tool.coverage.run]
source = ["chat_ui"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "pass",  # Simple pass statements
    "@abstractmethod",  # Abstract method definitions
]

# Critical paths requiring 70% coverage
include = [
    "chat_ui/services/message_service.py",
    "chat_ui/websocket_client.py",
    "chat_ui/config.py"
]
fail_under = 70
```

### Test Organization
- Unit tests for critical paths must be in corresponding test files
- Integration tests must cover critical path interactions
- Performance tests required for text batching and connection management

## Testing and Quality Assurance

### Testing Framework
- Use `pytest` and `pytest-asyncio` for all tests
- Coverage requirements:
  - 70% line coverage on critical logic paths only
  - Critical paths are defined in coverage configuration
- Run tests with:
  ```bash
  uv run pytest chat_ui/tests/ -v --cov=chat_ui
  ```

### Code Quality Tools
- Ruff with strict mode:
  ```bash
  uv run ruff check --strict
  ```
- MyPy with strict typing:
  ```bash
  uv run mypy --strict chat_ui/
  ```
- Optional mutation testing with mutmut:
  ```bash
  uv run mutmut run --paths-to-mutate="chat_ui/"
  ```

### Coverage Configuration
```toml
[tool.coverage.run]
source = ["chat_ui"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "pass",
    "@abstractmethod",
]

# Critical paths requiring 70% coverage
include = [
    "chat_ui/services/message_service.py",
    "chat_ui/websocket_client.py",
    "chat_ui/config.py"
]
fail_under = 70
```

## Logging and Observability

### Structured Logging
- Use `structlog` for all logging
- Configure JSON format output
- Include required fields:
  - `event`
  - `module`
  - `elapsed_ms`
  - `timestamp`

### Example Logging Configuration
```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

### Metrics and Monitoring
- Expose Prometheus metrics endpoint
- Track key metrics:
  - Message processing latency
  - WebSocket connection status
  - Error rates
  - Resource usage

### Example Metrics Configuration
```python
from prometheus_client import Counter, Histogram, start_http_server

# Message processing metrics
message_counter = Counter('chat_messages_total', 'Total messages processed')
message_latency = Histogram('message_processing_seconds', 'Message processing time')

# Start metrics server
start_http_server(8000)
```

## Code Organization and Style

### File Structure
- Single Responsibility: Files should contain closely related classes/functions
- Soft LOC cap:
  - Warning at 150 LOC if file has ≥ 2 public symbols
  - Hard review trigger at 300 LOC (override with justification)
- Complexity guardrails:
  - Cyclomatic complexity per file should stay below 15
  - No more than 3 public symbols per file
  - Exception: Domain modules may have up to 5 public symbols and 400 LOC

### Import Organization
- Order imports: stdlib → third-party → internal
- Group imports by type with a blank line between groups
- No wildcard imports (`from module import *`)

### Code Style
- Use `ruff` for consistent formatting
- Follow type hints strictly with `mypy --strict`
- Keep functions focused and under 50 lines
- Use descriptive variable names
- Document public APIs with docstrings

## Async and Concurrency Patterns

### Event-Driven Design
- Prefer event-driven patterns over polling
- Use async tasks, callbacks, and pub/sub where appropriate
- Handle cancellation and cleanup properly

### Async I/O Guidelines
- Use asyncio/anyio for external I/O > 10ms
- Never block the event loop
- Guard long operations:
  ```python
  async with timeout(TIMEOUT_SECONDS):
      await long_running_operation()
  ```

### Error Handling
- Shield critical sections
- Never swallow CancelledError
- Use proper exception hierarchy
- Log all errors with context

### Performance Requirements
- Backend API SLO: P95 latency ≤ 100ms
- Alert if SLO breached 3× within 15 min
- Optimize only after profiling shows > 2% CPU/time in pure functions

## Security Practices

### Environment Variables
- Never commit or overwrite `.env`
- Use `os.getenv()` for secrets
- Document required environment variables

### Logging Security
- Never log tokens or secrets
- Never log PII (Personally Identifiable Information)
- Mask sensitive data in logs

### Input Validation
- Validate all user input
- Use proper input sanitization
- Implement rate limiting where appropriate
