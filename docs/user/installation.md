# Installation Guide

## System Requirements

### Minimum Requirements
- Python 3.8 or higher
- 500MB free disk space
- SQLite3
- Internet connection for Telegram API access

### Optional Dependencies
- 7zip: Enhanced archive format support
- unrar: RAR archive support
- ffmpeg: Media file processing

## Installation Methods

### Method 1: Installing from PyPI (Recommended)
```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from PyPI
pip install telegram-archive-explorer
```

### Method 2: Installing from Source
```bash
# Clone the repository
git clone https://github.com/yourusername/telegram-archive-explorer.git
cd telegram-archive-explorer

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

## Platform-Specific Instructions

### Linux
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-venv sqlite3 p7zip-full unrar ffmpeg

# Fedora
sudo dnf install python3-venv sqlite p7zip p7zip-plugins unrar ffmpeg
```

### macOS
```bash
# Using Homebrew
brew install python sqlite p7zip unrar ffmpeg
```

### Windows
1. Download Python 3.8+ from [python.org](https://python.org)
2. During installation, check "Add Python to PATH"
3. Download and install [7-Zip](https://7-zip.org)
4. Download and install [SQLite](https://sqlite.org/download.html)
5. Optional: Install [WinRAR](https://www.win-rar.com)

## Post-Installation Setup

1. Verify installation:
```bash
telegram-explorer --version
```

2. Configure Telegram API credentials:
```bash
telegram-explorer setup
```

3. Follow the interactive setup process to:
   - Enter your Telegram API credentials
   - Configure database encryption
   - Set up initial channels

## Troubleshooting Installation

### Common Issues

1. **Python Version Mismatch**
   ```bash
   python --version  # Check Python version
   ```
   Solution: Install Python 3.8 or higher

2. **Missing Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **SQLite Issues**
   ```bash
   sqlite3 --version  # Check SQLite version
   ```
   Solution: Install SQLite 3.x

4. **Permission Issues**
   - Linux/macOS: Use `sudo` for system-wide installation
   - Windows: Run as Administrator

### Getting Help

If you encounter issues:
1. Check the [FAQ](faq.md)
2. Search [existing issues](https://github.com/yourusername/telegram-archive-explorer/issues)
3. Create a new issue with:
   - Your system information
   - Installation method used
   - Complete error message
   - Steps to reproduce
