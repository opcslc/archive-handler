"""
Tests for the Telegram API client module.

This module contains both unit tests with mocked responses and
integration tests for the Telegram client functionality.
"""

import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from telethon import TelegramClient
from telethon.tl.types import Message, Document, DocumentAttributeFilename

from telegram_archive_explorer.telegram_client import (
    TelegramArchiveClient,
    init_telegram_client,
    get_telegram_client
)
from telegram_archive_explorer.config import TelegramConfig, config

# Mock configuration for tests
TEST_CONFIG = TelegramConfig(
    api_id=12345,
    api_hash="test_hash",
    session_name="test_session"
)

@pytest.fixture
def mock_telegram_client():
    """Fixture for mocked TelegramClient."""
    with patch('telethon.TelegramClient', autospec=True) as mock_client:
        instance = mock_client.return_value
        instance.connect = AsyncMock(return_value=True)
        instance.is_user_authorized = AsyncMock(return_value=True)
        instance.disconnect = AsyncMock()
        yield instance

@pytest.fixture
def client(mock_telegram_client):
    """Fixture for TelegramArchiveClient with mocked TelegramClient."""
    return TelegramArchiveClient(TEST_CONFIG)

@pytest.mark.asyncio
async def test_connect_success(client, mock_telegram_client):
    """Test successful connection to Telegram API."""
    success = await client.connect()
    assert success
    mock_telegram_client.connect.assert_called_once()
    mock_telegram_client.is_user_authorized.assert_called_once()

@pytest.mark.asyncio
async def test_connect_unauthorized(client, mock_telegram_client):
    """Test connection when user is not authorized."""
    mock_telegram_client.is_user_authorized.return_value = False
    success = await client.connect()
    assert not success

@pytest.mark.asyncio
async def test_get_channel_success(client, mock_telegram_client):
    """Test getting a channel successfully."""
    mock_channel = Mock()
    mock_telegram_client.get_entity = AsyncMock(return_value=mock_channel)
    
    await client.connect()
    channel = await client.get_channel("test_channel")
    
    assert channel == mock_channel
    mock_telegram_client.get_entity.assert_called_once_with("test_channel")

@pytest.mark.asyncio
async def test_download_file_success(client, mock_telegram_client):
    """Test successful file download."""
    mock_message = Mock(spec=Message)
    mock_message.file = Mock(spec=Document)
    mock_message.document = Mock()
    mock_message.document.attributes = [
        Mock(spec=DocumentAttributeFilename, file_name="test.zip")
    ]
    
    download_path = Path("test.zip")
    mock_telegram_client.download_media = AsyncMock(return_value=str(download_path))
    
    await client.connect()
    result = await client.download_file(mock_message)
    
    assert result == download_path
    mock_telegram_client.download_media.assert_called_once()

@pytest.mark.asyncio
async def test_find_and_download_archives(client, mock_telegram_client):
    """Test finding and downloading archive files from a channel."""
    mock_channel = Mock()
    mock_telegram_client.get_entity = AsyncMock(return_value=mock_channel)
    
    mock_message = Mock(spec=Message)
    mock_message.id = 1
    mock_message.date = "2023-01-01"
    mock_message.file = Mock(size=1000)
    mock_message.document = Mock()
    mock_message.document.attributes = [
        Mock(spec=DocumentAttributeFilename, file_name="test.zip")
    ]
    
    mock_telegram_client.get_messages = AsyncMock(return_value=[mock_message])
    mock_telegram_client.download_media = AsyncMock(return_value="test.zip")
    
    await client.connect()
    results = await client.find_and_download_archives("test_channel", limit=10)
    
    assert len(results) == 1
    assert results[0]["message_id"] == 1
    assert results[0]["filename"] == "test.zip"
    assert results[0]["download_success"] is True
