"""
Command Line Interface for Telegram Archive Explorer.

This module provides the CLI interface for user interaction with the application.
It uses the Click library to create a rich command line experience.
"""

import os
import sys
import logging
import click
from typing import Optional

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

@cli.command('setup')
def setup_command():
    """
    Configure Telegram API credentials and other settings.
    
    This will guide you through the setup process for connecting to the Telegram API.
    You'll need to get your API ID and hash from https://my.telegram.org
    """
    click.echo("Setting up Telegram Archive Explorer...")
    
    # Create config directory if it doesn't exist
    config_dir = get_config_dir()
    
    # Check for existing API credentials
    if hasattr(config.telegram, 'api_id') and config.telegram.api_id:
        if click.confirm(f"API credentials already exist. Do you want to replace them?", default=False):
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
    
    # Ask about database encryption
    if click.confirm("Do you want to enable database encryption?", default=True):
        encryption_key = click.prompt(
            "Enter an encryption key for the database (keep this safe!)",
            hide_input=True, confirmation_prompt=True
        )
    else:
        encryption_key = None
    
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

@cli.command('channels')
@click.option('--list', 'list_channels', is_flag=True, help='List configured channels')
@click.option('--add', type=str, help='Add a channel by username or invite link')
@click.option('--remove', type=str, help='Remove a channel by username')
def channels_command(list_channels, add, remove):
    """
    Manage Telegram channels to monitor for archives.
    """
    # Placeholder for channel management functionality
    if list_channels:
        click.echo("Configured channels:")
        click.echo("  (Channel list will be shown here - not implemented yet)")
    
    if add:
        click.echo(f"Adding channel '{add}' (not implemented yet)")
    
    if remove:
        click.echo(f"Removing channel '{remove}' (not implemented yet)")

@cli.command('collect')
@click.option('--channel', type=str, help='Collect archives from a specific channel')
@click.option('--all', 'all_channels', is_flag=True, help='Collect archives from all configured channels')
def collect_command(channel, all_channels):
    """
    Collect archive files from Telegram channels.
    """
    if not channel and not all_channels:
        click.echo("Please specify a channel or use --all to collect from all channels")
        return
    
    if all_channels:
        click.echo("Collecting archives from all channels (not implemented yet)")
    else:
        click.echo(f"Collecting archives from channel '{channel}' (not implemented yet)")

@cli.command('search')
@click.argument('query', required=True)
@click.option('--url', is_flag=True, help='Search for a URL')
@click.option('--username', is_flag=True, help='Search for a username or email')
@click.option('--password', is_flag=True, help='Search for a password')
@click.option('--format', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
def search_command(query, url, username, password, format):
    """
    Search the database for URLs, usernames, emails, or passwords.
    
    QUERY is the search term. You can use wildcards (*) for pattern matching.
    """
    if not any([url, username, password]):
        # If no specific field selected, search everything
        url = username = password = True
    
    click.echo(f"Searching for '{query}' (not implemented yet)")
    click.echo(f"Search fields: URL={url}, Username/Email={username}, Password={password}")
    click.echo(f"Output format: {format}")

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
