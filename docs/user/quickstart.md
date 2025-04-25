# Quick Start Guide

Get started with Telegram Archive Explorer in minutes. This guide covers essential setup and basic operations.

## Installation

### Quick Install
```bash
# Using pip (recommended)
pip install telegram-archive-explorer

# Verify installation
telegram-explorer --version
```

### System Requirements
- Python 3.8+
- SQLite3
- Internet connection

## First-Time Setup

### 1. Get Telegram API Credentials
1. Visit [my.telegram.org](https://my.telegram.org)
2. Log in with your Telegram account
3. Go to "API development tools"
4. Create a new application
5. Note your API ID and API hash

### 2. Initial Configuration
```bash
# Run setup wizard
telegram-explorer setup

# Follow the prompts:
# 1. Enter API ID
# 2. Enter API hash
# 3. Configure database location
# 4. Set up encryption
```

## Basic Operations

### Managing Channels

```bash
# Add a channel
telegram-explorer channels --add "@channel_name"

# List your channels
telegram-explorer channels --list

# Check channel status
telegram-explorer channels --status "@channel_name"
```

### Collecting Data

```bash
# Collect from one channel
telegram-explorer collect --channel "@channel_name"

# Collect from all channels
telegram-explorer collect --all
```

### Basic Search

```bash
# Search by URL
telegram-explorer search --url "example.com"

# Search by username
telegram-explorer search --username "user123"

# Export results to CSV
telegram-explorer search --url "example.com" --format csv --output results.csv
```

## Automated Collection

### Set Up Scheduler
```bash
# Start automated collection every hour
telegram-explorer scheduler start --interval 60

# Check scheduler status
telegram-explorer scheduler status
```

## Common Tasks

### Data Export
```bash
# Export as CSV
telegram-explorer export --format csv --output data.csv

# Export as JSON
telegram-explorer export --format json --output data.json
```

### Backup Data
```bash
# Create backup
telegram-explorer backup create

# List backups
telegram-explorer backup list
```

## Troubleshooting

### Common Issues

1. **Connection Problems**
```bash
# Test connection
telegram-explorer diagnose --test-api
```

2. **Search Not Working**
```bash
# Rebuild search index
telegram-explorer maintenance rebuild-index
```

3. **Performance Issues**
```bash
# Optimize database
telegram-explorer maintenance optimize-db
```

## Next Steps

1. Read the full [Usage Guide](usage.md)
2. Watch [Video Tutorials](tutorials.md)
3. Check [Configuration Options](configuration.md)
4. Review [Command Reference](commands.md)

## Getting Help

- Check [FAQ](faq.md)
- Read [Troubleshooting Guide](troubleshooting.md)
- Report issues on [GitHub](https://github.com/yourusername/telegram-archive-explorer/issues)

## Quick Reference

### Essential Commands
```bash
# Setup
telegram-explorer setup

# Channel management
telegram-explorer channels --list
telegram-explorer channels --add "@channel"
telegram-explorer channels --remove "@channel"

# Data collection
telegram-explorer collect --channel "@channel"
telegram-explorer collect --all

# Search
telegram-explorer search --url "example.com"
telegram-explorer search --username "user123"

# Export
telegram-explorer export --format csv --output data.csv

# Maintenance
telegram-explorer maintenance optimize-db
telegram-explorer backup create
```

### Environment Variables
```bash
# API credentials
export TELEGRAM_EXPLORER_API_ID="your_api_id"
export TELEGRAM_EXPLORER_API_HASH="your_api_hash"

# Configuration
export TELEGRAM_EXPLORER_CONFIG="/path/to/config.yaml"
```

## Tips for Success

1. **Regular Maintenance**
   - Create regular backups
   - Optimize database weekly
   - Clean old archives

2. **Efficient Collection**
   - Use scheduled collection
   - Set appropriate intervals
   - Monitor disk space

3. **Best Practices**
   - Keep software updated
   - Check logs regularly
   - Document custom configurations

## Need More Help?

- Join our [Discord Community](https://discord.gg/telegramarchiveexplorer)
- Check [Stack Overflow](https://stackoverflow.com/questions/tagged/telegram-archive-explorer)
- Email support: support@telegramarchiveexplorer.com
