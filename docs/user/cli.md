# Command Line Interface Guide

## Basic Command Structure

All commands follow this basic structure:
```bash
telegram-explorer [global_options] command [command_options]
```

## Global Options

```bash
--config FILE     # Use alternative config file
--verbose, -v     # Increase output verbosity
--quiet, -q       # Suppress non-error output
--help, -h        # Show help message
--version         # Show version information
```

## Available Commands

### Setup and Configuration

#### setup
Initialize the application
```bash
# Interactive setup
telegram-explorer setup

# Non-interactive setup with environment variables
telegram-explorer setup --no-interactive
```

#### config
Manage configuration
```bash
# Edit configuration
telegram-explorer config edit

# Show current configuration
telegram-explorer config show

# Import configuration
telegram-explorer config import config.yaml

# Export configuration
telegram-explorer config export --output config.yaml
```

### Channel Management

#### channels
Manage Telegram channels
```bash
# List all channels
telegram-explorer channels --list

# Add channel
telegram-explorer channels --add "@channel_name"

# Remove channel
telegram-explorer channels --remove "@channel_name"

# Enable/disable channel
telegram-explorer channels --enable "@channel_name"
telegram-explorer channels --disable "@channel_name"

# Show channel status
telegram-explorer channels --status "@channel_name"

# Batch operations
telegram-explorer channels --add-file channels.txt
telegram-explorer channels --remove-file channels.txt
```

### Data Collection

#### collect
Collect archives from channels
```bash
# Collect from specific channel
telegram-explorer collect --channel "@channel_name"

# Collect from all channels
telegram-explorer collect --all

# Collect with date range
telegram-explorer collect \
    --channel "@channel_name" \
    --since "2023-01-01" \
    --until "2023-12-31"

# Limit collection
telegram-explorer collect \
    --channel "@channel_name" \
    --limit 100

# Force re-collection
telegram-explorer collect \
    --channel "@channel_name" \
    --force
```

### Search Operations

#### search
Search collected data
```bash
# Search by URL
telegram-explorer search --url "example.com"

# Search by username
telegram-explorer search --username "user123"

# Search by email
telegram-explorer search --email "@domain.com"

# Combined search
telegram-explorer search \
    --url "example.com" \
    --username "user*" \
    --date-range "2023-01-01,2023-12-31"

# Export results
telegram-explorer search \
    --url "example.com" \
    --format csv \
    --output "results.csv"
```

### Data Management

#### export
Export data in various formats
```bash
# Export to CSV
telegram-explorer export \
    --format csv \
    --output data.csv

# Export with filters
telegram-explorer export \
    --format json \
    --filter "date > '2023-01-01'" \
    --output filtered.json

# Export specific fields
telegram-explorer export \
    --format csv \
    --fields "url,username,date" \
    --output specific.csv
```

#### backup
Manage database backups
```bash
# Create backup
telegram-explorer backup create

# List backups
telegram-explorer backup list

# Restore backup
telegram-explorer backup restore backup_2023_01_01.db

# Clean old backups
telegram-explorer backup clean --older-than 30
```

### Scheduler Management

#### scheduler
Manage automatic collection
```bash
# Start scheduler
telegram-explorer scheduler start \
    --interval 60 \
    --channels "@channel1,@channel2"

# Stop scheduler
telegram-explorer scheduler stop

# Show status
telegram-explorer scheduler status

# List tasks
telegram-explorer scheduler list

# Modify schedule
telegram-explorer scheduler modify \
    --channel "@channel1" \
    --interval 120
```

### Maintenance

#### maintenance
System maintenance operations
```bash
# Optimize database
telegram-explorer maintenance optimize-db

# Clean temporary files
telegram-explorer maintenance clean-temp

# Rebuild search index
telegram-explorer maintenance rebuild-index

# Verify database
telegram-explorer maintenance verify-db
```

### Diagnostic Tools

#### diagnose
System diagnostics
```bash
# Run all checks
telegram-explorer diagnose

# Test specific components
telegram-explorer diagnose --test-api
telegram-explorer diagnose --test-db
telegram-explorer diagnose --test-network

# Generate report
telegram-explorer diagnose --generate-report
```

#### logs
Manage log files
```bash
# Show recent logs
telegram-explorer logs --show

# Follow log output
telegram-explorer logs --follow

# Export logs
telegram-explorer logs --export debug.log

# Filter logs
telegram-explorer logs --level ERROR --export errors.log
```

## Output Formats

### Table Format (Default)
```bash
telegram-explorer search --url "example.com"
```

### CSV Format
```bash
telegram-explorer search --url "example.com" \
    --format csv \
    --output results.csv
```

### JSON Format
```bash
telegram-explorer search --url "example.com" \
    --format json \
    --output results.json
```

## Environment Variables

```bash
# API credentials
export TELEGRAM_EXPLORER_API_ID="your_api_id"
export TELEGRAM_EXPLORER_API_HASH="your_api_hash"

# Configuration
export TELEGRAM_EXPLORER_CONFIG="/path/to/config.yaml"
export TELEGRAM_EXPLORER_LOG_LEVEL="DEBUG"
```

## Exit Codes

- 0: Success
- 1: General error
- 2: Configuration error
- 3: Network error
- 4: Database error
- 5: Permission error

## See Also
- [Configuration Guide](configuration.md)
- [Usage Guide](usage.md)
- [Troubleshooting Guide](troubleshooting.md)
