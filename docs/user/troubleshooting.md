# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with Telegram Archive Explorer.

## Quick Diagnostics

Run the built-in diagnostic tool:
```bash
telegram-explorer diagnose --generate-report
```

## Common Issues and Solutions

### Installation Problems

#### Python Version Errors
```
Error: Python 3.8 or higher is required
```
**Solution:**
1. Check Python version:
   ```bash
   python --version
   ```
2. Install/upgrade Python from [python.org](https://python.org)
3. Ensure correct Python is in PATH

#### Dependencies Installation Fails
```
Error: Failed to build wheel for cryptography
```
**Solution:**
1. Update pip:
   ```bash
   python -m pip install --upgrade pip
   ```
2. Install build dependencies:
   ```bash
   # Linux
   sudo apt-get install python3-dev libffi-dev build-essential
   # macOS
   brew install openssl
   # Windows
   # Install Visual C++ Build Tools
   ```

### Authentication Issues

#### API Credentials Invalid
```
Error: API ID/hash combination is invalid
```
**Solution:**
1. Verify credentials at [my.telegram.org](https://my.telegram.org)
2. Rerun setup:
   ```bash
   telegram-explorer setup
   ```
3. Check config file for typos

#### Session Expired
```
Error: Session expired, please re-authenticate
```
**Solution:**
1. Remove session file:
   ```bash
   rm ~/.telegram-explorer/session.session
   ```
2. Restart application
3. Re-authenticate when prompted

### Database Issues

#### Database Locked
```
Error: database is locked
```
**Solution:**
1. Check for other running instances
2. Kill blocking processes
3. If persists, repair database:
   ```bash
   telegram-explorer maintenance repair-db
   ```

#### Encryption Errors
```
Error: Unable to decrypt database
```
**Solution:**
1. Verify encryption key location
2. Check file permissions
3. Restore from backup if necessary:
   ```bash
   telegram-explorer backup restore latest
   ```

### Channel Collection Issues

#### Rate Limiting
```
Error: Too many requests (flood wait)
```
**Solution:**
1. Increase collection interval
2. Reduce concurrent operations
3. Wait for flood wait to expire

#### Network Problems
```
Error: Connection failed
```
**Solution:**
1. Check internet connection
2. Verify proxy settings if used
3. Test API connectivity:
   ```bash
   telegram-explorer diagnose --test-api
   ```

### Search Issues

#### Search Times Out
```
Error: Search operation timed out
```
**Solution:**
1. Narrow search criteria
2. Increase timeout in config
3. Optimize database:
   ```bash
   telegram-explorer maintenance optimize-db
   ```

#### No Results Found
**Solution:**
1. Verify data collection status
2. Check search syntax
3. Ensure indexes are built:
   ```bash
   telegram-explorer maintenance rebuild-index
   ```

### System Resource Issues

#### High Memory Usage
**Solution:**
1. Reduce batch sizes
2. Clear cache:
   ```bash
   telegram-explorer maintenance clean-cache
   ```
3. Monitor memory usage

#### Disk Space
```
Error: No space left on device
```
**Solution:**
1. Clear temporary files
2. Clean old archives:
   ```bash
   telegram-explorer maintenance clean-archives
   ```
3. Configure backup retention

## Log File Analysis

### Accessing Logs
```bash
# View recent logs
telegram-explorer logs --show

# Follow live logs
telegram-explorer logs --follow

# Export logs for analysis
telegram-explorer logs --export debug.log
```

### Common Log Patterns

#### Error Patterns
```
ERROR: Connection refused
```
- Check network connectivity
- Verify firewall settings

```
ERROR: Permission denied
```
- Check file permissions
- Verify user privileges

```
ERROR: Database corruption detected
```
- Run integrity check
- Restore from backup

## Performance Optimization

### Slow Operations
1. Enable debug logging
2. Monitor resource usage
3. Adjust batch sizes
4. Optimize database regularly

### Memory Management
1. Configure cache limits
2. Schedule regular cleanup
3. Monitor system resources

## Recovery Procedures

### Database Recovery
1. Stop all operations
2. Backup current state
3. Run repair tools
4. Verify data integrity
5. Restore if necessary

### Configuration Recovery
1. Export current config
2. Reset to defaults
3. Reconfigure step by step
4. Test functionality

## Getting Support

### Before Seeking Help
1. Check this guide
2. Review logs
3. Generate diagnostic report
4. Search existing issues

### Reporting Issues
Include:
1. Diagnostic report
2. Error messages
3. Steps to reproduce
4. System information

### Community Support
- GitHub Issues
- Documentation Wiki
- Community Forums
- Email Support

## Preventive Maintenance

### Regular Tasks
1. Update software regularly
2. Monitor disk space
3. Check log files
4. Verify backups
5. Test recovery procedures

### Best Practices
1. Regular backups
2. Monitor resource usage
3. Keep logs rotated
4. Update configurations
5. Test recovery procedures

## See Also
- [Configuration Guide](configuration.md)
- [Command Reference](commands.md)
- [FAQ](faq.md)
