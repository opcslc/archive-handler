import asyncio
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from telegram_archive_explorer.scheduler import ArchiveCollectionScheduler, TaskResult

@pytest.fixture
def mock_telegram_client():
    with patch('telegram_archive_explorer.scheduler.get_telegram_client') as mock:
        client = AsyncMock()
        client.connect.return_value = True
        client.find_and_download_archives.return_value = []
        mock.return_value = client
        yield client

@pytest.fixture
def scheduler(tmp_path):
    config_file = tmp_path / "scheduler.json"
    scheduler = ArchiveCollectionScheduler(config_file)
    # Configure for testing
    scheduler.config.collection_interval = 1  # 1 hour for testing
    scheduler.config.initial_retry_delay = 1  # 1 minute for testing
    scheduler.config.retry_backoff_factor = 2
    scheduler.config.max_retries = 3
    scheduler.config.max_concurrent_collections = 2
    scheduler.config.collection_timeout = 5
    scheduler.config.max_retry_delay = 10
    scheduler.config.prioritize_failed = True
    return scheduler

@pytest.mark.asyncio
async def test_collection_success(scheduler, mock_telegram_client):
    """Test successful archive collection"""
    mock_telegram_client.find_and_download_archives.return_value = [
        {'file': 'archive1.zip', 'download_success': True},
        {'file': 'archive2.zip', 'download_success': True}
    ]
    
    scheduler.add_channel('@test_channel')
    result = await scheduler._collect_from_channel('@test_channel')
    
    assert result.success
    assert result.result_data['files_found'] == 2
    assert result.result_data['files_downloaded'] == 2
    mock_telegram_client.find_and_download_archives.assert_called_once_with('@test_channel')

@pytest.mark.asyncio
async def test_collection_failure_and_retry(scheduler, mock_telegram_client):
    """Test collection failure and retry mechanism"""
    # Make the first attempt fail
    mock_telegram_client.find_and_download_archives.side_effect = [
        Exception("Network error"),
        [{'file': 'archive1.zip', 'download_success': True}]
    ]
    
    scheduler.add_channel('@test_channel')
    
    # First attempt - should fail
    result = await scheduler._collect_from_channel('@test_channel')
    assert not result.success
    assert "Network error" in result.error
    
    # Check retry was scheduled
    retries = scheduler.retry_tracker.get_all_retries()
    assert len(retries) == 1
    assert retries[0]['task_name'] == 'collect_from_channel:@test_channel'
    assert retries[0]['attempt_number'] == 1
    
    # Process retry - should succeed
    await scheduler._process_retries()
    
    # Verify retry succeeded
    retries = scheduler.retry_tracker.get_all_retries()
    assert len(retries) == 0

@pytest.mark.asyncio
async def test_retry_backoff(scheduler, mock_telegram_client):
    """Test exponential backoff for retries"""
    # Make all attempts fail
    mock_telegram_client.find_and_download_archives.side_effect = Exception("Network error")
    
    scheduler.add_channel('@test_channel')
    
    # First attempt
    start_time = datetime.now()
    result = await scheduler._collect_from_channel('@test_channel')
    assert not result.success
    
    # Check retry delays
    retries = scheduler.retry_tracker.get_all_retries()
    retry_delays = []
    
    for i in range(scheduler.config.max_retries):
        retry = retries[0]
        delay = (retry['next_attempt'] - start_time).total_seconds() / 60  # Convert to minutes
        retry_delays.append(delay)
        
        if i < scheduler.config.max_retries - 1:
            await scheduler._process_retries()
            await asyncio.sleep(0.1)  # Small delay to allow processing
    
    # Verify exponential backoff
    assert retry_delays[0] == pytest.approx(1, rel=0.1)  # Initial delay 1 minute
    assert retry_delays[1] == pytest.approx(2, rel=0.1)  # Second delay 2 minutes
    assert retry_delays[2] == pytest.approx(4, rel=0.1)  # Third delay 4 minutes

@pytest.mark.asyncio
async def test_concurrent_collection(scheduler, mock_telegram_client):
    """Test concurrent collection from multiple channels"""
    # Add multiple channels
    scheduler.add_channel('@test_channel1')
    scheduler.add_channel('@test_channel2')
    scheduler.add_channel('@test_channel3')
    
    # Configure mock to track concurrent calls
    calls_in_progress = 0
    max_concurrent_calls = 0
    
    async def mock_download(channel):
        nonlocal calls_in_progress, max_concurrent_calls
        calls_in_progress += 1
        max_concurrent_calls = max(max_concurrent_calls, calls_in_progress)
        await asyncio.sleep(0.1)  # Simulate work
        calls_in_progress -= 1
        return [{'file': f'{channel}_archive.zip', 'download_success': True}]
    
    mock_telegram_client.find_and_download_archives.side_effect = mock_download
    
    # Run collection
    await scheduler._collect_from_all_channels()
    
    # Verify concurrent execution
    assert max_concurrent_calls == scheduler.config.max_concurrent_collections
    assert mock_telegram_client.find_and_download_archives.call_count == 3

@pytest.mark.asyncio
async def test_collection_timeout(scheduler, mock_telegram_client):
    """Test collection timeout handling"""
    scheduler.add_channel('@test_channel')
    
    # Make mock take longer than timeout
    async def slow_download(_):
        await asyncio.sleep(10)
        return []
    
    mock_telegram_client.find_and_download_archives.side_effect = slow_download
    
    # Run collection - should timeout
    await scheduler._collect_from_all_channels()
    
    # Verify timeout was handled
    retries = scheduler.retry_tracker.get_all_retries()
    assert len(retries) == 1
    assert "timed out" in retries[0]['error'].lower()

@pytest.mark.asyncio
async def test_status_reporting(scheduler, mock_telegram_client):
    """Test status reporting methods"""
    # Add channels and generate some activity
    scheduler.add_channel('@test_channel1')
    scheduler.add_channel('@test_channel2')
    
    # Success case
    mock_telegram_client.find_and_download_archives.return_value = [
        {'file': 'archive1.zip', 'download_success': True}
    ]
    await scheduler._collect_from_channel('@test_channel1')
    
    # Failure case
    mock_telegram_client.find_and_download_archives.side_effect = Exception("Network error")
    await scheduler._collect_from_channel('@test_channel2')
    
    # Get overall status
    status = scheduler.get_status()
    assert len(status['channels']) == 2
    assert status['stats']['total_collections'] == 1
    assert status['stats']['total_failures'] == 1
    
    # Get channel-specific status
    ch1_status = scheduler.get_channel_status('@test_channel1')
    assert ch1_status['statistics']['success_rate'] == "100.0%"
    assert len(ch1_status['collection_history']) == 1
    
    ch2_status = scheduler.get_channel_status('@test_channel2')
    assert ch2_status['statistics']['success_rate'] == "0.0%"
    assert len(ch2_status['pending_retries']) == 1

@pytest.mark.asyncio
async def test_daemon_mode(scheduler, mock_telegram_client):
    """Test daemon mode operation"""
    mock_telegram_client.find_and_download_archives.return_value = [
        {'file': 'archive1.zip', 'download_success': True}
    ]
    
    scheduler.add_channel('@test_channel')
    
    # Start scheduler
    scheduler.start(run_immediately=True)
    await asyncio.sleep(0.5)  # Allow immediate collection to complete
    
    # Verify immediate collection happened
    mock_telegram_client.find_and_download_archives.assert_called_once()
    
    # Stop scheduler
    scheduler.stop()
    assert not scheduler.running

def test_scheduler_config(tmp_path):
    """Test scheduler configuration"""
    config_file = tmp_path / "scheduler.json"
    scheduler = ArchiveCollectionScheduler(config_file)
    
    # Test channel management
    scheduler.add_channel('@test_channel1')
    scheduler.add_channel('@test_channel2')
    assert len(scheduler.config.channels) == 2
    
    scheduler.remove_channel('@test_channel1')
    assert len(scheduler.config.channels) == 1
    assert '@test_channel2' in scheduler.config.channels
    
    # Test config persistence
    new_scheduler = ArchiveCollectionScheduler(config_file)
    assert len(new_scheduler.config.channels) == 1
    assert '@test_channel2' in new_scheduler.config.channels
