# Usage Guide

## Basic Operations

### Channel Management

1. **Adding Channels**
```bash
# Add a public channel
telegram-explorer channels --add "@public_channel"

# Add a private channel (requires invitation link)
telegram-explorer channels --add "https://t.me/joinchat/..."
```

2. **Managing Channels**
```bash
# List all channels
telegram-explorer channels --list

# Remove a channel
telegram-explorer channels --remove "@channel_name"

# Check channel status
telegram-explorer channels --status "@channel_name"
```

### Data Collection

1. **Manual Collection**
```bash
# Collect from specific channel
telegram-explorer collect --channel "@channel_name"

# Collect from all channels
telegram-explorer collect --all

# Collect with date range
telegram-explorer collect --channel "@channel_name" \
    --since "2023-01-01" \
    --until "2023-12-31"
```

2. **Automated Collection**
```bash
# Set up scheduled collection
telegram-explorer scheduler start \
    --interval 60 \
    --channels "@channel1,@channel2"

# Check scheduler status
telegram-explorer scheduler status
```

## Search Operations

### Basic Search

1. **URL Search**
```bash
# Basic URL search
telegram-explorer search --url "example.com"

# URL search with wildcards
telegram-explorer search --url "*.example.com"
```

2. **Username Search**
```bash
# Exact username match
telegram-explorer search --username "user123"

# Pattern matching
telegram-explorer search --username "user*"
```

3. **Email Search**
```bash
# Search by email domain
telegram-explorer search --email "@example.com"

# Search by email pattern
telegram-explorer search --email "john*@*.com"
```

### Advanced Search

1. **Combined Search**
```bash
# Multiple criteria
telegram-explorer search \
    --url "example.com" \
    --username "user*" \
    --date-range "2023-01-01,2023-12-31"
```

2. **Export Options**
```bash
# Export as CSV
telegram-explorer search --url "example.com" \
    --format csv \
    --output "results.csv"

# Export as JSON
telegram-explorer search --url "example.com" \
    --format json \
    --output "results.json"
```

## Data Management

### Backup Operations

1. **Creating Backups**
```bash
# Create full backup
telegram-explorer backup create

# Create backup with name
telegram-explorer backup create --name "pre_update"
```

2. **Managing Backups**
```bash
# List backups
telegram-explorer backup list

# Restore from backup
telegram-explorer backup restore "backup_name"

# Delete old backups
telegram-explorer backup clean --older-than 30
```

### Database Maintenance

1. **Optimization**
```bash
# Optimize database
telegram-explorer maintenance optimize-db

# Rebuild search index
telegram-explorer maintenance rebuild-index
```

2. **Cleanup**
```bash
# Clean temporary files
telegram-explorer maintenance clean-temp

# Remove old archives
telegram-explorer maintenance clean-archives \
    --older-than 90
```

## Advanced Features

### Custom Workflows

1. **Data Export**
```bash
# Export specific data range
telegram-explorer export \
    --format json \
    --date-range "2023-01-01,2023-12-31" \
    --output "export.json"

# Export with filters
telegram-explorer export \
    --format csv \
    --filter "url LIKE '%.gov'" \
    --output "gov_urls.csv"
```

2. **Batch Operations**
```bash
# Batch channel addition
telegram-explorer channels --add-file "channels.txt"

# Batch data collection
telegram-explorer collect --from-file "targets.txt"
```

### System Integration

1. **Logging Configuration**
```bash
# Enable debug logging
telegram-explorer --verbose

# Export logs
telegram-explorer logs --export "debug.log"
```

2. **Monitoring**
```bash
# Check system status
telegram-explorer status

# Monitor collection progress
telegram-explorer collect --monitor
```

## Best Practices

### Data Collection

1. **Efficient Collection**
- Use appropriate intervals
- Group similar channels
- Monitor rate limits
- Use incremental collection

2. **Resource Management**
- Regular cleanup
- Monitor disk space
- Optimize database regularly
- Use appropriate batch sizes

### Search Operations

1. **Search Optimization**
- Use specific criteria
- Utilize proper indexes
- Export large results
- Cache common searches

2. **Data Organization**
- Regular backups
- Structured exports
- Clean old data
- Maintain indexes

## Common Workflows

### Initial Setup
1. Configure API credentials
2. Add initial channels
3. Set up scheduled collection
4. Configure backup schedule

### Daily Operations
1. Monitor collection status
2. Check for new data
3. Perform searches
4. Export results

### Maintenance Tasks
1. Database optimization
2. Cleanup old files
3. Verify backups
4. Update configurations

## Tips and Tricks

### Performance
- Use specific search criteria
- Export large datasets
- Regular maintenance
- Monitor resource usage

### Organization
- Consistent naming
- Regular backups
- Clean old data
- Document customizations

### Troubleshooting
- Check logs first
- Verify connectivity
- Monitor resources
- Test in isolation

## See Also
- [Command Reference](commands.md)
- [Configuration Guide](configuration.md)
- [Troubleshooting Guide](troubleshooting.md)
- [FAQ](faq.md)
