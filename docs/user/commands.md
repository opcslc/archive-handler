# Command Reference

This guide details all available commands in the Telegram Archive Explorer CLI.

## Global Options

These options are available for all commands:

```bash
--verbose, -v     # Increase output verbosity
--quiet, -q       # Suppress non-error output
--config FILE     # Use alternative config file
--help, -h        # Show command help
--version         # Show version information
```

## Command Categories

### Setup and Configuration

#### setup
Initialize application and configure API credentials
```bash
telegram-explorer setup [--no-interactive]
```
Options:
- `--no-interactive`: Use environment variables instead of prompts

#### config
Manage configuration settings
```bash
telegram-explorer config [SUBCOMMAND]

# Subcommands:
edit              # Open config in default editor
show              # Display current configuration
reset             # Reset to default configuration
import FILE       # Import configuration from file
export FILE       # Export configuration to file
```

### Channel Management

#### channels
Manage Telegram channels
```bash
telegram-explorer channels [OPTIONS]

Options:
--list                    # List configured channels
--add CHANNEL            # Add a channel
--remove CHANNEL         # Remove a channel
--enable CHANNEL         # Enable channel monitoring
--disable CHANNEL        # Disable channel monitoring
--status CHANNEL         # Show channel status
```

### Data Collection

#### collect
Collect archives from channels
```bash
telegram-explorer collect [OPTIONS]

Options:
--channel CHANNEL        # Collect from specific channel
--all                   # Collect from all channels
--since DATE            # Collect archives after date
--until DATE            # Collect archives before date
--limit N              # Maximum archives to collect
--force                # Re-collect existing archives
```

#### extract
Extract collected archives
```bash
telegram-explorer extract [OPTIONS]

Options:
--input FILE           # Extract specific archive
--all                  # Extract all pending archives
--format FORMAT        # Specify archive format
--output DIR          # Custom output directory
```

### Data Management

#### search
Search collected data
```bash
telegram-explorer search [OPTIONS] QUERY

Options:
--url URL             # Search by URL
--username USER       # Search by username
--email EMAIL         # Search by email
--password PASS       # Search by password
--format FORMAT       # Output format (json/csv/table)
--limit N            # Maximum results
--export FILE        # Export results to file
```

#### export
Export data to various formats
```bash
telegram-explorer export [OPTIONS]

Options:
--format FORMAT       # Export format (json/csv/sql)
--output FILE        # Output file path
--compress           # Compress output
--filter FILTER      # Filter data to export
```

### Scheduler Management

#### scheduler
Manage automatic collection scheduler
```bash
telegram-explorer scheduler [SUBCOMMAND]

Subcommands:
start               # Start scheduler
stop                # Stop scheduler
status              # Show scheduler status
list                # List scheduled tasks
add                 # Add new scheduled task
remove              # Remove scheduled task
```

### Maintenance

#### backup
Manage database backups
```bash
telegram-explorer backup [SUBCOMMAND]

Subcommands:
create              # Create new backup
restore FILE        # Restore from backup
list                # List available backups
clean               # Remove old backups
```

#### maintenance
System maintenance operations
```bash
telegram-explorer maintenance [SUBCOMMAND]

Subcommands:
clean-cache         # Clear application cache
verify-db          # Verify database integrity
optimize-db        # Optimize database
repair-db          # Attempt database repair
```

### Diagnostic Tools

#### diagnose
System diagnostic tools
```bash
telegram-explorer diagnose [OPTIONS]

Options:
--test-api          # Test Telegram API connection
--test-db           # Test database connection
--test-network      # Test network connectivity
--generate-report   # Generate diagnostic report
```

#### logs
Log file management
```bash
telegram-explorer logs [OPTIONS]

Options:
--show              # Display recent logs
--follow            # Follow log output
--level LEVEL       # Filter by log level
--export FILE       # Export logs to file
```

## Exit Codes

- 0: Success
- 1: General error
- 2: Configuration error
- 3: Network error
- 4: Database error
- 5: Permission error
- 6: Input/validation error

## Examples

### Basic Usage
```bash
# Setup application
telegram-explorer setup

# Add and collect from a channel
telegram-explorer channels --add "@example_channel"
telegram-explorer collect --channel "@example_channel"

# Search collected data
telegram-explorer search --url "example.com"
```

### Advanced Usage
```bash
# Configure scheduled collection
telegram-explorer scheduler add --channel "@example_channel" --interval 60

# Export specific data
telegram-explorer export --format json --filter "date > '2023-01-01'"

# Maintenance tasks
telegram-explorer maintenance clean-cache
telegram-explorer backup create
```

## See Also

- [Configuration Guide](configuration.md)
- [Troubleshooting Guide](troubleshooting.md)
- [FAQ](faq.md)
