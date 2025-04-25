# Configuration Guide

## Initial Setup

### Telegram API Configuration
1. Obtain API credentials from [my.telegram.org](https://my.telegram.org):
   - Log in with your Telegram account
   - Go to "API development tools"
   - Create a new application
   - Note your API ID and API hash

2. Run the configuration wizard:
```bash
telegram-explorer setup
```

## Configuration File

The configuration file is located at:
- Linux/macOS: `~/.config/telegram-explorer/config.yaml`
- Windows: `%APPDATA%\telegram-explorer\config.yaml`

### Example Configuration
```yaml
telegram:
  api_id: "your_api_id"
  api_hash: "your_api_hash"
  # Optional: proxy settings
  proxy:
    enabled: false
    type: socks5  # or http
    host: "127.0.0.1"
    port: 9050

database:
  path: "~/.local/share/telegram-explorer/data.db"
  encryption_key_file: "~/.config/telegram-explorer/key.enc"
  auto_backup: true
  backup_retention_days: 30

channels:
  - "@channel1"
  - "@channel2"
  # Add more channels as needed

scheduler:
  enabled: true
  interval_minutes: 60
  retry_attempts: 3
  retry_delay_minutes: 5

logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  file: "~/.local/share/telegram-explorer/explorer.log"
  max_size_mb: 10
  backup_count: 5

search:
  max_results: 1000
  timeout_seconds: 30
  cache_enabled: true
  cache_duration_hours: 24
```

## Configuration Options

### Telegram Settings
- `api_id`: Your Telegram API ID
- `api_hash`: Your Telegram API hash
- `proxy`: Optional proxy configuration
  - `enabled`: Enable/disable proxy
  - `type`: Proxy type (socks5/http)
  - `host`: Proxy server host
  - `port`: Proxy server port

### Database Settings
- `path`: SQLite database location
- `encryption_key_file`: Path to encryption key
- `auto_backup`: Enable automatic backups
- `backup_retention_days`: Days to keep backups

### Channel Settings
- List of Telegram channels to monitor
- Use full channel names including "@"
- Public and private channels supported

### Scheduler Settings
- `enabled`: Enable/disable automatic collection
- `interval_minutes`: Time between collections
- `retry_attempts`: Failed operation retry count
- `retry_delay_minutes`: Delay between retries

### Logging Settings
- `level`: Logging detail level
- `file`: Log file location
- `max_size_mb`: Maximum log file size
- `backup_count`: Number of log backups to keep

### Search Settings
- `max_results`: Maximum search results
- `timeout_seconds`: Search operation timeout
- `cache_enabled`: Enable result caching
- `cache_duration_hours`: Cache retention period

## Environment Variables

Override configuration using environment variables:
```bash
# Telegram API credentials
export TELEGRAM_EXPLORER_API_ID="your_api_id"
export TELEGRAM_EXPLORER_API_HASH="your_api_hash"

# Database settings
export TELEGRAM_EXPLORER_DB_PATH="/custom/path/to/db"
export TELEGRAM_EXPLORER_ENCRYPTION_KEY="/custom/path/to/key"

# Logging
export TELEGRAM_EXPLORER_LOG_LEVEL="DEBUG"
```

## Security Considerations

1. **API Credentials**
   - Keep API credentials secure
   - Don't share config files
   - Use environment variables in production

2. **Database Encryption**
   - Keep encryption key secure
   - Backup encryption key separately
   - Rotate keys periodically

3. **Access Control**
   - Restrict config file permissions
   - Use separate user accounts
   - Monitor access logs

## Updating Configuration

1. Manual editing:
```bash
telegram-explorer config edit
```

2. Command-line updates:
```bash
# Add channel
telegram-explorer config channel --add "@newchannel"

# Update scheduler interval
telegram-explorer config scheduler --interval 120

# Enable debug logging
telegram-explorer config logging --level DEBUG
```

## Troubleshooting

- Check log files for configuration errors
- Verify file permissions
- Ensure valid YAML syntax
- Test proxy settings if configured
- Validate API credentials
