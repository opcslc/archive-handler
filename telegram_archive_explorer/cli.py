"""
Command Line Interface for Telegram Archive Explorer.

This module provides the CLI interface for user interaction with the application.
It uses the Click library to create a rich command line experience.
"""

import os
import sys
import json
import logging
import click
from typing import Optional, Dict, Union, Any

from . import __version__
from .config import config, get_config_dir
from .logging_setup import setup_logging, stats
from .database import init_db

logger = logging.getLogger(__name__)

# Set up click context settings
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
@click.option('--log-level', type=str, help='Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
@click.option('--log-file', type=str, help='Path to log file')
@click.option('--config-file', type=str, help='Path to config file')
def cli(log_level: Optional[str], log_file: Optional[str], config_file: Optional[str]):
    """
    Telegram Archive Explorer - A tool for exploring and searching Telegram channel archives.
    
    This tool allows you to connect to Telegram channels, download archive files,
    extract credentials, and search them efficiently.
    """
    # Set up logging
    setup_logging(log_file, log_level)
    
    logger.info(f"Telegram Archive Explorer v{__version__} starting up")
    
    # Initialize the database
    init_db()

@cli.group()
def configure():
    """
    Manage application configuration.
    
    This command group provides options for viewing and modifying configuration settings.
    Settings can be managed via config file, environment variables, or command line.
    """
    pass


@configure.command('setup')
@click.option('--non-interactive', is_flag=True, help='Run setup without prompts using environment variables')
def setup_command(non_interactive: bool) -> None:
    """
    Configure Telegram API credentials and other settings.
    
    This will guide you through the setup process for connecting to the Telegram API.
    You'll need to get your API ID and hash from https://my.telegram.org
    
    Can be run non-interactively using environment variables:
    - TELEGRAM_API_ID
    - TELEGRAM_API_HASH
    - DATABASE_ENCRYPTION_KEY (optional)
    """
    click.echo("Setting up Telegram Archive Explorer...")
    config_dir = get_config_dir()
    config_data: Dict[str, Dict[str, Union[str, int, None]]] = {
        "telegram": {
            "api_id": None,
            "api_hash": None
        },
        "database": {
            "path": str(config_dir / "database.db"),
            "encryption_key": None
        }
    }

    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    encryption_key: Optional[str] = None

    if non_interactive:
        # Use environment variables
        api_id_str = os.environ.get('TELEGRAM_API_ID')
        api_hash = os.environ.get('TELEGRAM_API_HASH')
        encryption_key = os.environ.get('DATABASE_ENCRYPTION_KEY')
        
        if not api_id_str or not api_hash:
            click.echo("Error: TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables must be set", err=True)
            sys.exit(1)
            
        try:
            api_id = int(api_id_str)
        except ValueError:
            click.echo("Error: TELEGRAM_API_ID must be an integer", err=True)
            sys.exit(1)
    else:
        # Interactive setup
        if hasattr(config.telegram, 'api_id') and config.telegram.api_id:
            if click.confirm("API credentials already exist. Do you want to replace them?", default=False):
                api_id = click.prompt("Enter your Telegram API ID", type=int)
                api_hash = click.prompt("Enter your Telegram API hash", type=str)
            else:
                api_id = config.telegram.api_id
                api_hash = config.telegram.api_hash
        else:
            click.echo("You need Telegram API credentials to use this tool.")
            click.echo("Get them from https://my.telegram.org")
            api_id = click.prompt("Enter your Telegram API ID", type=int)
            api_hash = click.prompt("Enter your Telegram API hash", type=str)
        
        if click.confirm("Do you want to enable database encryption?", default=True):
            encryption_key = click.prompt(
                "Enter an encryption key for the database (keep this safe!)",
                hide_input=True, confirmation_prompt=True
            )

    if api_id is not None:
        config_data["telegram"]["api_id"] = api_id
    if api_hash is not None:
        config_data["telegram"]["api_hash"] = api_hash
    if encryption_key is not None:
        config_data["database"]["encryption_key"] = encryption_key
    
    # Write configuration to file
    import json
    config_data = {
        "telegram": {
            "api_id": api_id,
            "api_hash": api_hash,
        },
        "database": {
            "path": str(config_dir / "database.db"),
            "encryption_key": encryption_key
        }
    }
    
    with open(config_dir / "config.json", 'w') as f:
        json.dump(config_data, f, indent=2)
    
    click.echo(f"Configuration saved to {config_dir / 'config.json'}")
    click.echo("Setup complete!")

@configure.command('show')
@click.option('--show-secrets', is_flag=True, help='Show sensitive values (API keys, etc)')
def show_config(show_secrets: bool) -> None:
    """Show current configuration settings."""
    def mask_secret(value: Optional[Union[str, int]]) -> str:
        if value and not show_secrets:
            return "********"
        return str(value) if value is not None else ""

    config_data = {
        "telegram": {
            "api_id": mask_secret(config.telegram.api_id),
            "api_hash": mask_secret(config.telegram.api_hash),
            "session_name": config.telegram.session_name
        },
        "database": {
            "path": config.database.path,
            "encryption_key": mask_secret(config.database.encryption_key)
        },
        "log_level": config.log_level,
        "log_file": config.log_file,
        "temp_dir": config.temp_dir
    }
    
    click.echo(json.dumps(config_data, indent=2))

@configure.command('set')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']))
@click.option('--log-file', type=click.Path())
@click.option('--temp-dir', type=click.Path())
@click.option('--session-name', type=str, help='Telegram session name for multi-account support')
def set_config(log_level: Optional[str], log_file: Optional[str], temp_dir: Optional[str], session_name: Optional[str]) -> None:
    """
    Modify configuration settings.
    
    Updates the configuration file with the provided values.
    Only specified options will be modified; other settings remain unchanged.
    """
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        config_data = {}
    
    if log_level:
        config_data["log_level"] = log_level
    if log_file:
        config_data["log_file"] = str(log_file)
    if temp_dir:
        config_data["temp_dir"] = str(temp_dir)
    if session_name:
        if "telegram" not in config_data:
            config_data["telegram"] = {}
        config_data["telegram"]["session_name"] = session_name
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    click.echo("Configuration updated successfully")



@cli.group()
def channels():
    """
    Manage Telegram channels to monitor for archives.
    
    Commands for adding, removing, and listing monitored channels.
    """
    pass

@channels.command('list')
@click.option('--json', 'json_output', is_flag=True, help='Output in JSON format')
def list_channels(json_output: bool) -> None:
    """List all configured channels."""
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        config_data = {}
    
    channels = config_data.get("channels", [])
    
    if not channels:
        click.echo("No channels configured.")
        return
    
    if json_output:
        click.echo(json.dumps(channels, indent=2))
    else:
        click.echo("Configured channels:")
        for channel in channels:
            click.echo(f"  - {channel}")

@channels.command('add')
@click.argument('channel')
def add_channel(channel: str) -> None:
    """
    Add a channel to monitor.
    
    CHANNEL can be a username (@example) or invite link.
    """
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        config_data = {}
    
    if "channels" not in config_data:
        config_data["channels"] = []
    
    if channel in config_data["channels"]:
        click.echo(f"Channel '{channel}' is already configured.")
        return
    
    config_data["channels"].append(channel)
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    click.echo(f"Added channel: {channel}")

@channels.command('remove')
@click.argument('channel')
def remove_channel(channel: str) -> None:
    """
    Remove a monitored channel.
    
    CHANNEL must match exactly the username or link used when adding.
    """
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        config_data = {}
    
    if "channels" not in config_data or channel not in config_data["channels"]:
        click.echo(f"Channel '{channel}' is not configured.")
        return
    
    config_data["channels"].remove(channel)
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    click.echo(f"Removed channel: {channel}")

@cli.group()
def collect():
    """
    Collect archive files from Telegram channels.
    
    Commands for manual and scheduled archive collection.
    """
    pass

@collect.command('now')
@click.option('--channel', type=str, help='Collect from a specific channel')
@click.option('--all', 'all_channels', is_flag=True, help='Collect from all configured channels')
@click.option('--verbose', is_flag=True, help='Show detailed progress')
def collect_now(channel: Optional[str], all_channels: bool, verbose: bool) -> None:
    """
    Immediately collect archives from channels.
    
    Either specify a single channel or use --all for all configured channels.
    """
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        click.echo("No configuration found. Please run 'configure setup' first.", err=True)
        sys.exit(1)
    
    channels = config_data.get("channels", [])
    if not channels:
        click.echo("No channels configured. Use 'channels add' to add channels.", err=True)
        sys.exit(1)
    
    if not channel and not all_channels:
        click.echo("Please specify a channel or use --all to collect from all channels", err=True)
        sys.exit(1)
    
    target_channels = channels if all_channels else [channel] if channel in channels else []
    if not target_channels:
        click.echo(f"Channel '{channel}' is not configured. Use 'channels add' to add it.", err=True)
        sys.exit(1)
    
    for ch in target_channels:
        if verbose:
            click.echo(f"Collecting from {ch}...")
        try:
            # TODO: Implement actual collection logic here
            click.echo(f"Successfully collected from {ch}")
        except Exception as e:
            click.echo(f"Error collecting from {ch}: {e}", err=True)

@collect.command('schedule')
@click.argument('cron')
@click.option('--enable/--disable', default=True, help='Enable or disable scheduled collection')
def schedule_collection(cron: str, enable: bool) -> None:
    """
    Configure scheduled archive collection.
    
    CRON is a cron expression (e.g. '0 */6 * * *' for every 6 hours).
    Common patterns:
    - '0 * * * *'      Every hour
    - '0 */6 * * *'    Every 6 hours
    - '0 0 * * *'      Every day at midnight
    - '0 0 * * MON'    Every Monday at midnight
    
    Use --disable to turn off scheduled collection.
    """
    if enable and cron != "disable":
        # Validate cron expression
        try:
            import croniter
            if not croniter.is_valid(cron):
                raise ValueError("Invalid cron expression")
        except ImportError:
            click.echo("Warning: croniter package not installed. Cron validation skipped.", err=True)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"
    
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        config_data = {}
    
    if not enable:
        config_data.pop("schedule", None)
        click.echo("Scheduled collection disabled")
    else:
        config_data["schedule"] = cron
        click.echo(f"Collection scheduled: {cron}")
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)

@cli.group()
def search():
    """
    Search the database for archived content.
    
    Commands for searching and filtering archive data.
    """
    pass

@search.command('query')
@click.argument('pattern')
@click.option('--url', is_flag=True, help='Search for URLs')
@click.option('--username', is_flag=True, help='Search for usernames/emails')
@click.option('--password', is_flag=True, help='Search for passwords')
@click.option('--channel', help='Limit search to specific channel')
@click.option('--before', type=click.DateTime(), help='Only results before date')
@click.option('--after', type=click.DateTime(), help='Only results after date')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
@click.option('--limit', type=int, default=100, help='Maximum number of results')
@click.option('--count', is_flag=True, help='Only show result count')
def search_query(
    pattern: str,
    url: bool,
    username: bool,
    password: bool,
    channel: Optional[str],
    before: Optional[str],
    after: Optional[str],
    format: str,
    limit: int,
    count: bool
) -> None:
    """
    Search archive content with pattern matching.
    
    PATTERN supports wildcards (*) and regular expressions.
    At least one search type (--url, --username, --password) must be specified.
    """
    if not any([url, username, password]):
        click.echo("Error: Specify at least one search type (--url, --username, --password)", err=True)
        sys.exit(1)

    # TODO: Implement actual search logic here
    # For now, just demonstrate the command structure
    search_params = {
        "pattern": pattern,
        "types": {
            "url": url,
            "username": username,
            "password": password
        },
        "filters": {
            "channel": channel,
            "before": before,
            "after": after
        },
        "limit": limit
    }
    
    if count:
        click.echo("Found 0 matches")  # TODO: Implement actual counting
        return
    
    if format == 'json':
        click.echo(json.dumps(search_params, indent=2, default=str))
    elif format == 'csv':
        click.echo("timestamp,channel,type,value")  # TODO: Implement CSV output
    else:  # table format
        click.echo("Search Results:")
        click.echo("No results found")  # TODO: Implement table output

@search.command('export')
@click.argument('output', type=click.Path())
@click.option('--format', type=click.Choice(['json', 'csv']), default='csv')
def export_results(output: str, format: str) -> None:
    """
    Export last search results to a file.
    
    OUTPUT is the path to save the export file.
    """
    click.echo(f"Exporting results to {output} in {format} format")
    # TODO: Implement export functionality

def main():
    """Main entry point."""
    try:
        cli()
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
