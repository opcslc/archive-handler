# Frequently Asked Questions (FAQ)

## General Questions

### What is Telegram Archive Explorer?
A tool that helps you collect, parse, and search data from Telegram channel archives. It automates the process of downloading archives, extracting data, and making it searchable.

### Is it free to use?
Yes, Telegram Archive Explorer is open-source and free to use. However, you need your own Telegram API credentials.

### Which operating systems are supported?
- Linux (Ubuntu, Debian, Fedora, etc.)
- macOS (10.14 Mojave or later)
- Windows (10 or later)

## Setup and Installation

### How do I get Telegram API credentials?
1. Visit [my.telegram.org](https://my.telegram.org)
2. Log in with your Telegram account
3. Go to "API development tools"
4. Create a new application
5. Note your API ID and API hash

### Why does installation fail with cryptography errors?
This usually means you're missing build dependencies. See the [Troubleshooting Guide](troubleshooting.md) for detailed solutions.

### Can I use a proxy connection?
Yes, the application supports both SOCKS5 and HTTP proxies. Configure them in your config file or during setup.

## Usage Questions

### How many channels can I monitor?
There's no hard limit on the number of channels, but consider:
- Your available disk space
- Telegram API rate limits
- System resources

### What archive formats are supported?
- ZIP
- RAR
- 7Z
- TAR
- GZ
- BZ2
- XZ

### How do I search for specific data?
Use the search command with appropriate flags:
```bash
# Search for URLs
telegram-explorer search --url "example.com"

# Search for usernames
telegram-explorer search --username "user123"

# Search for emails
telegram-explorer search --email "@domain.com"
```

### Can I export search results?
Yes, use the `--format` flag with search commands:
```bash
telegram-explorer search --url "example.com" --format csv --export results.csv
```

## Data and Privacy

### Is my data encrypted?
Yes, all stored data is encrypted using AES-256 encryption at rest.

### Where is data stored?
Default locations:
- Linux: `~/.local/share/telegram-explorer/`
- macOS: `~/Library/Application Support/telegram-explorer/`
- Windows: `%APPDATA%\telegram-explorer\`

### How do I backup my data?
Use the built-in backup commands:
```bash
telegram-explorer backup create
```

### Can I delete all stored data?
Yes, either:
1. Use maintenance commands:
   ```bash
   telegram-explorer maintenance clean-all
   ```
2. Manually delete the data directory

## Performance

### Why is collection slow?
Common reasons:
- Telegram API rate limits
- Large archive files
- Network connectivity
- System resource constraints

### How can I improve search performance?
1. Keep the database optimized:
   ```bash
   telegram-explorer maintenance optimize-db
   ```
2. Use specific search criteria
3. Maintain adequate disk space
4. Regular index rebuilding

### How much disk space do I need?
Recommendations:
- Minimum: 500MB
- Recommended: 2GB+
- Depends on:
  - Number of channels
  - Archive sizes
  - Retention period

## Scheduler

### How does automatic collection work?
The scheduler:
1. Runs in the background
2. Checks channels at configured intervals
3. Downloads new archives
4. Processes data automatically

### Can I schedule different intervals per channel?
Yes, configure individual schedules:
```bash
telegram-explorer scheduler add --channel "@channel" --interval 120
```

### What happens if collection fails?
The scheduler:
1. Logs the error
2. Retries based on configuration
3. Continues with other channels
4. Notifies based on settings

## Troubleshooting

### How do I check if everything is working?
Run the diagnostic tool:
```bash
telegram-explorer diagnose --generate-report
```

### Where are the log files?
Default log locations:
- Linux: `~/.local/share/telegram-explorer/logs/`
- macOS: `~/Library/Logs/telegram-explorer/`
- Windows: `%APPDATA%\telegram-explorer\logs\`

### How do I report bugs?
1. Generate a diagnostic report
2. Check existing GitHub issues
3. Create new issue with:
   - Error messages
   - Steps to reproduce
   - System information

## Development

### Can I contribute to the project?
Yes! We welcome contributions:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request
4. Follow contribution guidelines

### Is there an API for integration?
Yes, see the [API Reference](../dev/api.md) for integration options.

### Can I extend the functionality?
Yes, through:
- Custom plugins
- API integration
- Source code modifications

## Support

### Where can I get help?
- [Documentation](../README.md)
- [Troubleshooting Guide](troubleshooting.md)
- GitHub Issues
- Community Forums

### Is commercial support available?
Contact the maintainers for commercial support options.

### How do I stay updated?
- Watch the GitHub repository
- Follow release announcements
- Join the community channels
