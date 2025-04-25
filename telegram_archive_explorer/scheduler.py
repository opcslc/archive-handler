"""
Scheduler for periodic archive collection.

This module implements a scheduler that can periodically collect archives from
configured Telegram channels.
"""

import logging
import time
import asyncio
import threading
import signal
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from pathlib import Path
import json

import schedule

from .config import config
from .logging_setup import stats
from .telegram_client import get_telegram_client, init_telegram_client

logger = logging.getLogger(__name__)

class TaskResult:
    """Result of a scheduled task execution."""
    
    def __init__(self, task_name: str):
        """
        Initialize task result.
        
        Args:
            task_name: Name of the task
        """
        self.task_name = task_name
        self.success = False
        self.start_time = datetime.now()
        self.end_time = None
        self.duration = None
        self.error = None
        self.result_data = {}
    
    def complete(self, success: bool, result_data: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """
        Mark the task as complete.
        
        Args:
            success: Whether the task completed successfully
            result_data: Optional data resulting from the task
            error: Optional error message if the task failed
        """
        self.success = success
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.error = error
        
        if result_data:
            self.result_data = result_data
    
    def __str__(self) -> str:
        """
        String representation of the task result.
        
        Returns:
            Formatted string with task result information
        """
        status = "succeeded" if self.success else "failed"
        duration = f"{self.duration:.2f} seconds" if self.duration else "ongoing"
        
        result = f"Task '{self.task_name}' {status} after {duration}"
        if self.error:
            result += f" - Error: {self.error}"
            
        return result

class RetryTracker:
    """Tracks retry attempts for failed tasks."""
    
    def __init__(self):
        """Initialize retry tracker."""
        self.retries = {}  # Dict mapping task IDs to retry information
    
    def add_retry(self, task_id: str, task_name: str, 
                 next_attempt: datetime, 
                 attempt_number: int, 
                 max_attempts: int,
                 error: Optional[str] = None):
        """
        Add a task to the retry tracker.
        
        Args:
            task_id: Unique identifier for the task
            task_name: Name of the task
            next_attempt: When the next retry will occur
            attempt_number: Which attempt this will be (1-based)
            max_attempts: Maximum number of attempts
            error: Optional error message from the previous attempt
        """
        self.retries[task_id] = {
            'task_id': task_id,
            'task_name': task_name,
            'next_attempt': next_attempt,
            'attempt_number': attempt_number,
            'max_attempts': max_attempts,
            'error': error,
            'added': datetime.now()
        }
    
    def get_pending_retries(self) -> List[Dict[str, Any]]:
        """
        Get list of retries that are pending.
        
        Returns:
            List of retry information dictionaries
        """
        now = datetime.now()
        return [retry for retry in self.retries.values() 
                if retry['next_attempt'] <= now]
    
    def get_all_retries(self) -> List[Dict[str, Any]]:
        """
        Get all tracked retries.
        
        Returns:
            List of all retry information dictionaries
        """
        return list(self.retries.values())
    
    def remove_retry(self, task_id: str):
        """
        Remove a task from the retry tracker.
        
        Args:
            task_id: Task ID to remove
        """
        if task_id in self.retries:
            del self.retries[task_id]
    
    def update_retry(self, task_id: str, 
                    next_attempt: datetime, 
                    attempt_number: int,
                    error: Optional[str] = None):
        """
        Update a retry entry.
        
        Args:
            task_id: Task ID to update
            next_attempt: When the next retry will occur
            attempt_number: Which attempt this will be (1-based)
            error: Optional error message from the previous attempt
        """
        if task_id in self.retries:
            self.retries[task_id].update({
                'next_attempt': next_attempt,
                'attempt_number': attempt_number,
                'error': error,
                'updated': datetime.now()
            })

class SchedulerConfig:
    """Configuration for the scheduler."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize scheduler configuration.
        
        Args:
            config_file: Optional path to configuration file.
                         If None, uses default location in the config directory.
        """
        if config_file:
            self.config_file = config_file
        else:
            from .config import get_config_dir
            self.config_file = get_config_dir() / "scheduler.json"
            
        self.channels = []
        self.collection_interval = 24  # hours
        self.max_retries = 5
        self.initial_retry_delay = 5  # minutes
        self.retry_backoff_factor = 2
        self.daemon_mode = False
        
        # Load configuration if file exists
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        if not self.config_file.exists():
            logger.info(f"Scheduler config file not found at {self.config_file}. Using defaults.")
            return
            
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                
            # Update attributes from config
            if 'channels' in config:
                self.channels = config['channels']
                
            if 'collection_interval' in config:
                self.collection_interval = config['collection_interval']
                
            if 'max_retries' in config:
                self.max_retries = config['max_retries']
                
            if 'initial_retry_delay' in config:
                self.initial_retry_delay = config['initial_retry_delay']
                
            if 'retry_backoff_factor' in config:
                self.retry_backoff_factor = config['retry_backoff_factor']
                
            if 'daemon_mode' in config:
                self.daemon_mode = config['daemon_mode']
                
            logger.info(f"Loaded scheduler configuration from {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to load scheduler config: {e}")
    
    def save_config(self):
        """Save configuration to file."""
        try:
            # Create parent directory if it doesn't exist
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                'channels': self.channels,
                'collection_interval': self.collection_interval,
                'max_retries': self.max_retries,
                'initial_retry_delay': self.initial_retry_delay,
                'retry_backoff_factor': self.retry_backoff_factor,
                'daemon_mode': self.daemon_mode
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
            logger.info(f"Saved scheduler configuration to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save scheduler config: {e}")
    
    def add_channel(self, channel: str):
        """
        Add a channel to the configuration.
        
        Args:
            channel: Channel identifier
        """
        if channel not in self.channels:
            self.channels.append(channel)
            self.save_config()
    
    def remove_channel(self, channel: str):
        """
        Remove a channel from the configuration.
        
        Args:
            channel: Channel identifier
        """
        if channel in self.channels:
            self.channels.remove(channel)
            self.save_config()

class ArchiveCollectionScheduler:
    """Scheduler for periodic archive collection from Telegram channels."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize the scheduler.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config = SchedulerConfig(config_file)
        self.retry_tracker = RetryTracker()
        self.running = False
        self.stop_event = threading.Event()
        self.scheduler_thread = None
        self.loop = None
        self.task_history = []  # List of recent task results
        self.history_limit = 100  # Maximum number of task results to keep
    
    def _calculate_next_retry(self, attempt: int) -> datetime:
        """
        Calculate the time for the next retry attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Datetime for the next retry
        """
        delay = self.config.initial_retry_delay * (self.config.retry_backoff_factor ** attempt)
        return datetime.now() + timedelta(minutes=delay)
    
    def _handle_task_failure(self, task_name: str, task_id: str, error: str):
        """
        Handle a task failure by scheduling a retry if appropriate.
        
        Args:
            task_name: Name of the task
            task_id: Unique identifier for the task
            error: Error message
        """
        # Check if task is already in retry tracker
        retries = self.retry_tracker.get_all_retries()
        retry_info = next((r for r in retries if r['task_id'] == task_id), None)
        
        if retry_info:
            attempt = retry_info['attempt_number']
            if attempt < self.config.max_retries:
                # Schedule another retry
                next_attempt = self._calculate_next_retry(attempt)
                self.retry_tracker.update_retry(
                    task_id,
                    next_attempt,
                    attempt + 1,
                    error
                )
                logger.info(f"Scheduled retry {attempt + 1}/{self.config.max_retries} for {task_name} at {next_attempt}")
            else:
                # Max retries exceeded
                logger.error(f"Max retries exceeded for {task_name}. Giving up.")
                self.retry_tracker.remove_retry(task_id)
        else:
            # First failure, schedule first retry
            next_attempt = self._calculate_next_retry(0)
            self.retry_tracker.add_retry(
                task_id,
                task_name,
                next_attempt,
                1,
                self.config.max_retries,
                error
            )
            logger.info(f"Scheduled first retry for {task_name} at {next_attempt}")
    
    async def _collect_from_channel(self, channel: str) -> TaskResult:
        """
        Collect archives from a single channel.
        
        Args:
            channel: Channel identifier
            
        Returns:
            TaskResult with task execution result
        """
        task_name = f"collect_from_channel:{channel}"
        result = TaskResult(task_name)
        
        try:
            # Get Telegram client
            client = get_telegram_client()
            
            # Make sure client is connected
            if not await client.connect():
                raise Exception("Failed to connect to Telegram API")
            
            # Download archives
            logger.info(f"Collecting archives from channel: {channel}")
            download_results = await client.find_and_download_archives(channel)
            
            # Record results
            result.complete(
                success=True,
                result_data={
                    'channel': channel,
                    'files_found': len(download_results),
                    'files_downloaded': sum(1 for r in download_results if r['download_success']),
                    'download_results': download_results
                }
            )
            
            # Update stats
            stats.increment("channels_collected")
            stats.increment("archive_files_found", len(download_results))
            stats.increment("archive_files_downloaded", 
                          sum(1 for r in download_results if r['download_success']))
            
            logger.info(f"Collected {len(download_results)} archives from {channel}")
            
        except Exception as e:
            logger.error(f"Error collecting from channel {channel}: {e}")
            result.complete(success=False, error=str(e))
            self._handle_task_failure(task_name, f"channel:{channel}", str(e))
        
        # Add to task history
        self.task_history.append({
            'task_name': result.task_name,
            'success': result.success,
            'start_time': result.start_time,
            'end_time': result.end_time,
            'duration': result.duration,
            'error': result.error
        })
        
        # Trim history if needed
        if len(self.task_history) > self.history_limit:
            self.task_history = self.task_history[-self.history_limit:]
        
        return result
    
    async def _collect_from_all_channels(self):
        """Collect archives from all configured channels."""
        logger.info(f"Starting collection from {len(self.config.channels)} channels")
        
        for channel in self.config.channels:
            if self.stop_event.is_set():
                logger.info("Stop requested, aborting remaining channel collections")
                break
                
            await self._collect_from_channel(channel)
    
    async def _process_retries(self):
        """Process any pending retry attempts."""
        pending_retries = self.retry_tracker.get_pending_retries()
        
        if not pending_retries:
            return
            
        logger.info(f"Processing {len(pending_retries)} pending retries")
        
        for retry in pending_retries:
            task_id = retry['task_id']
            task_name = retry['task_name']
            
            # Check if this is a channel collection task
            if task_name.startswith('collect_from_channel:'):
                channel = task_name.split(':', 1)[1]
                logger.info(f"Retrying collection from channel {channel} (attempt {retry['attempt_number']})")
                
                result = await self._collect_from_channel(channel)
                
                if result.success:
                    # Success, remove from retry tracker
                    self.retry_tracker.remove_retry(task_id)
                    logger.info(f"Retry succeeded for {task_name}")
    
    async def _run_scheduler_async(self):
        """Run the scheduler asynchronously."""
        # Initialize telegram client
        await init_telegram_client()
        
        while not self.stop_event.is_set():
            try:
                # Process any pending retries
                await self._process_retries()
                
                # Sleep for 1 minute
                for _ in range(60):
                    if self.stop_event.is_set():
                        break
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Sleep before retry
    
    def _run_scheduler(self):
        """Run the scheduler in a separate thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Schedule periodic collection
        def run_collection():
            logger.info("Running scheduled collection")
            if self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self._collect_from_all_channels(), self.loop)
            
        # Set up the schedule
        schedule.every(self.config.collection_interval).hours.do(run_collection)
        
        # Run scheduler async loop
        self.loop.run_until_complete(self._run_scheduler_async())
        self.loop.close()
    
    def start(self, run_immediately: bool = False):
        """
        Start the scheduler.
        
        Args:
            run_immediately: Whether to run a collection immediately
        """
        if self.running:
            logger.warning("Scheduler is already running")
            return
            
        logger.info("Starting scheduler")
        self.running = True
        self.stop_event.clear()
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        # Run initial collection if requested
        if run_immediately and self.config.channels:
            logger.info("Running immediate collection")
            
            # Create a new event loop for the main thread
            main_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(main_loop)
            
            try:
                main_loop.run_until_complete(self._collect_from_all_channels())
            finally:
                main_loop.close()
    
    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
            
        logger.info("Stopping scheduler")
        self.stop_event.set()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=30)
            
        self.running = False
        logger.info("Scheduler stopped")
    
    def add_channel(self, channel: str):
        """
        Add a channel to be monitored.
        
        Args:
            channel: Channel identifier
        """
        self.config.add_channel(channel)
        logger.info(f"Added channel {channel} to scheduler")
    
    def remove_channel(self, channel: str):
        """
        Remove a channel from monitoring.
        
        Args:
            channel: Channel identifier
        """
        self.config.remove_channel(channel)
        logger.info(f"Removed channel {channel} from scheduler")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the scheduler.
        
        Returns:
            Dictionary with scheduler status information
        """
        return {
            'running': self.running,
            'channels': self.config.channels,
            'collection_interval': self.config.collection_interval,
            'next_run': schedule.next_run().strftime('%Y-%m-%d %H:%M:%S') if self.running else None,
            'pending_retries': len(self.retry_tracker.get_pending_retries()),
            'total_retries': len(self.retry_tracker.get_all_retries()),
            'task_history': self.task_history[-10:]  # Last 10 tasks
        }
    
    def get_task_history(self) -> List[Dict[str, Any]]:
        """
        Get the task execution history.
        
        Returns:
            List of task history entries
        """
        return self.task_history
    
    def run_collection_now(self, channel: Optional[str] = None):
        """
        Run a collection immediately.
        
        Args:
            channel: Optional specific channel to collect from.
                    If None, collects from all configured channels.
        """
        # Create a new event loop for the main thread
        main_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(main_loop)
        
        try:
            if channel:
                logger.info(f"Running immediate collection from channel {channel}")
                main_loop.run_until_complete(self._collect_from_channel(channel))
            else:
                logger.info("Running immediate collection from all channels")
                main_loop.run_until_complete(self._collect_from_all_channels())
        finally:
            main_loop.close()
