# Project Rules and Configuration

## Python Version
- Using Python 3.13.5 (pinned exactly)
- Do not mix Python versions across environments

## Dependency Management
### Core Dependencies
- Kivy==2.3.1 (required for Python 3.13 compatibility)
- KivyMD==1.2.0 (auto-upgrades to 2.0.1.dev0 for Python 3.13)
- websockets==13.1

### Package Management
- Use `uv` for all Python package management
- Never use pip, poetry, or conda directly
- No need to activate virtual environment when using `uv`
- Always pin exact versions in pyproject.toml

### Installation Commands
```bash
# Install dependencies
uv pip install "kivy==2.3.1"
uv pip install "kivymd==1.2.0" "websockets==13.1"

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
1. KivyMD 1.2.0 automatically upgrades to 2.0.1.dev0 when used with Python 3.13
2. The virtual environment is managed automatically by `uv`
3. Always use exact version pins (==) instead of version ranges
4. System dependencies must be installed before Python packages

## Development Workflow
1. Install system dependencies first
2. Use `uv` for all Python package management
3. Run the app with `uv run python main.py`
4. Keep this document updated with any new dependencies or version changes
