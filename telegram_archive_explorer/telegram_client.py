"""
Telegram API client for channel access and archive downloads.

This module interfaces with the Telegram API using the Telethon library to
connect to channels, retrieve message history, and download files.
"""

import os
import logging
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable, Union
from datetime import datetime, timedelta

import telethon
from telethon import TelegramClient
from telethon.tl.types import Message, DocumentAttributeFilename
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.errors import (
    FloodWaitError, 
    AuthKeyUnregisteredError, 
    PhoneNumberBannedError,
    SessionPasswordNeededError
)

from .config import config, TelegramConfig
from .logging_setup import stats

logger = logging.getLogger(__name__)

# File extensions we consider as potential archive files
ARCHIVE_EXTENSIONS = {
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
    '.tar.gz', '.tar.bz2', '.tar.xz', '.tgz', '.tbz2', '.txz'
}

class TelegramArchiveClient:
    """Client for interacting with Telegram API to download archives."""
    
    def __init__(self, telegram_config: Optional[TelegramConfig] = None):
        """
        Initialize the Telegram client.
        
        Args:
            telegram_config: Optional telegram configuration.
                            If None, uses the configuration from the config module.
        """
        self.config = telegram_config or config.telegram
        self.client = None
        self._connected = False
        
        # Set up downloads directory
        self.downloads_dir = Path(config.temp_dir) / "downloads"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
        # Retry configuration
        self.max_retries = 5
        self.initial_retry_delay = 1  # seconds
    
    async def connect(self) -> bool:
        """
        Connect to Telegram API.
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        if self._connected:
            return True
            
        if not self.config.api_id or not self.config.api_hash:
            logger.error("Telegram API credentials not configured. Run 'telegram-explorer setup' first.")
            return False
        
        # Set up session file path
        session_path = Path(config.temp_dir) / self.config.session_name
        session_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Create client
            self.client = TelegramClient(
                str(session_path),
                self.config.api_id,
                self.config.api_hash
            )
            
            # Connect and sign in
            await self.client.connect()
            
            # Check authorization
            if not await self.client.is_user_authorized():
                logger.error("Not authorized. You need to log in first.")
                # Note: Actual login process would require user interaction
                # and should be handled by the CLI interface
                return False
            
            self._connected = True
            logger.info("Connected to Telegram API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Telegram API: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Telegram API."""
        if self.client:
            await self.client.disconnect()
            self._connected = False
            logger.info("Disconnected from Telegram API")
    
    async def get_channel(self, channel_identifier: str):
        """
        Get a channel entity by username, invite link, or ID.
        
        Args:
            channel_identifier: Channel username, invite link, or ID.
            
        Returns:
            Channel entity or None if not found.
        """
        if not self._connected:
            if not await self.connect():
                return None
        
        try:
            # Handle different types of identifiers
            if channel_identifier.startswith('https://t.me/'):
                # Extract username from invite link
                parts = channel_identifier.split('/')
                channel_identifier = parts[-1]
            
            # Get the entity
            channel = await self.client.get_entity(channel_identifier)
            return channel
            
        except Exception as e:
            logger.error(f"Failed to get channel {channel_identifier}: {e}")
            return None
    
    async def list_channels(self):
        """
        List all dialogs (chats and channels) the user is part of.
        
        Returns:
            List of dialog entities.
        """
        if not self._connected:
            if not await self.connect():
                return []
        
        try:
            dialogs = await self.client.get_dialogs()
            return dialogs
        except Exception as e:
            logger.error(f"Failed to list channels: {e}")
            return []
    
    async def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Execute a function with exponential backoff retry logic.
        
        Args:
            func: Async function to call
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call or raises the last exception.
        """
        retry_delay = self.initial_retry_delay
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except FloodWaitError as e:
                wait_time = e.seconds
                logger.warning(f"Rate limited by Telegram. Waiting {wait_time} seconds.")
                await asyncio.sleep(wait_time)
            except Exception as e:
                if attempt + 1 < self.max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"All {self.max_retries} attempts failed. Last error: {e}")
                    raise
    
    async def get_messages(self, channel, limit: int = 100, offset_id: int = 0):
        """
        Get messages from a channel with retry logic.
        
        Args:
            channel: Channel entity
            limit: Maximum number of messages to retrieve
            offset_id: Start from this message ID
            
        Returns:
            List of messages
        """
        if not self._connected:
            if not await self.connect():
                return []
        
        try:
            return await self._retry_with_backoff(
                self.client.get_messages,
                channel,
                limit=limit,
                offset_id=offset_id
            )
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def _is_archive_file(self, message: Message) -> bool:
        """
        Check if a message contains an archive file.
        
        Args:
            message: Telegram message
            
        Returns:
            bool: True if message contains an archive file, False otherwise
        """
        if not message.file:
            return False
            
        # Check for filename attribute
        for attr in message.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                filename = attr.file_name.lower()
                # Check file extension
                return any(filename.endswith(ext) for ext in ARCHIVE_EXTENSIONS)
                
        return False
    
    async def download_file(self, message: Message, destination: Optional[Path] = None) -> Optional[Path]:
        """
        Download a file from a message with retry logic.
        
        Args:
            message: Telegram message containing a file
            destination: Optional destination path or directory
                        If None, saves to the downloads directory
            
        Returns:
            Path to the downloaded file or None if download failed
        """
        if not self._connected:
            if not await self.connect():
                return None
                
        if not message.file:
            logger.error("Message does not contain a file")
            return None
            
        # Determine filename
        filename = None
        for attr in message.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                filename = attr.file_name
                break
                
        if not filename:
            # Generate a filename based on message ID if no filename found
            filename = f"file_{message.id}_{int(time.time())}"
        
        # Determine destination path
        if destination:
            if destination.is_dir():
                dest_path = destination / filename
            else:
                dest_path = destination
        else:
            dest_path = self.downloads_dir / filename
            
        # Create parent directory if it doesn't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Download the file with retry logic
            download_path = await self._retry_with_backoff(
                self.client.download_media,
                message,
                str(dest_path)
            )
            
            if download_path:
                logger.info(f"Downloaded file to {download_path}")
                stats.increment("files_downloaded")
                return Path(download_path)
            else:
                logger.error("Download failed")
                return None
                
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return None
    
    async def find_and_download_archives(self, 
                                         channel_identifier: str,
                                         limit: int = 100, 
                                         download_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Find and download archive files from a channel.
        
        Args:
            channel_identifier: Channel username, invite link, or ID
            limit: Maximum number of messages to check
            download_dir: Optional directory to save downloaded files
                         If None, saves to the downloads directory
            
        Returns:
            List of dictionaries with information about downloaded files:
                {
                    'message_id': int,
                    'date': datetime,
                    'filename': str,
                    'file_path': Path,
                    'size': int,
                    'download_success': bool
                }
        """
        if not self._connected:
            if not await self.connect():
                return []
                
        # Get channel
        channel = await self.get_channel(channel_identifier)
        if not channel:
            logger.error(f"Channel not found: {channel_identifier}")
            return []
            
        # Determine download directory
        if download_dir:
            dest_dir = download_dir
        else:
            dest_dir = self.downloads_dir
            
        # Create directory if it doesn't exist
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Get messages
        logger.info(f"Retrieving up to {limit} messages from {channel_identifier}")
        messages = await self.get_messages(channel, limit=limit)
        
        # Find archives
        archive_messages = [msg for msg in messages if self._is_archive_file(msg)]
        logger.info(f"Found {len(archive_messages)} archive files in {len(messages)} messages")
        
        # Download archives
        results = []
        for message in archive_messages:
            # Get filename
            filename = None
            for attr in message.document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    filename = attr.file_name
                    break
                    
            if not filename:
                filename = f"file_{message.id}_{int(time.time())}"
                
            logger.info(f"Downloading {filename} from message {message.id}")
            
            # Download file
            file_path = await self.download_file(message, dest_dir)
            
            # Record result
            results.append({
                'message_id': message.id,
                'date': message.date,
                'filename': filename,
                'file_path': file_path,
                'size': message.file.size if message.file else 0,
                'download_success': file_path is not None
            })
            
        logger.info(f"Downloaded {sum(1 for r in results if r['download_success'])} out of {len(results)} archive files")
        return results

# Global client instance
telegram_client = None

async def init_telegram_client(telegram_config: Optional[TelegramConfig] = None):
    """
    Initialize and connect the Telegram client.
    
    Args:
        telegram_config: Optional telegram configuration.
                        If None, uses the configuration from the config module.
                        
    Returns:
        Connected TelegramArchiveClient instance
    """
    global telegram_client
    telegram_client = TelegramArchiveClient(telegram_config)
    await telegram_client.connect()
    return telegram_client

def get_telegram_client():
    """Get the global Telegram client instance."""
    global telegram_client
    if telegram_client is None:
        # This will be properly initialized asynchronously by the application
        telegram_client = TelegramArchiveClient()
    return telegram_client
