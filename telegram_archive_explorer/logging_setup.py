"""
Logging configuration for Telegram Archive Explorer.

This module sets up rotating file logs and console output with different
configurable levels, including structured logging, error aggregation,
and statistics collection.
"""

import os
import sys
import json
import logging
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler, MemoryHandler
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import deque

from .config import config

class StructuredFormatter(logging.Formatter):
    """Custom formatter that supports structured logging with extra fields."""
    
    def format(self, record):
        # Get the standard formatted message
        message = super().format(record)
        
        # Add structured data if present
        extra = {
            key: value for key, value in record.__dict__.items()
            if key not in logging.LogRecord.__dict__ and key != 'extra'
        }
        
        if extra:
            try:
                structured_data = json.dumps(extra)
                message = f"{message} | {structured_data}"
            except (TypeError, ValueError):
                pass
                
        return message

class ErrorAggregator:
    """Aggregates error messages and their frequencies."""
    
    def __init__(self, max_size: int = 1000):
        self.errors: Dict[str, int] = {}
        self.max_size = max_size
        self.lock = threading.Lock()
        self.recent_errors: deque = deque(maxlen=100)  # Keep last 100 errors with full context
        
    def add_error(self, error_msg: str, error_context: Dict[str, Any] = None):
        """Add an error occurrence with optional context."""
        with self.lock:
            if len(self.errors) >= self.max_size and error_msg not in self.errors:
                # Remove least frequent error if at capacity
                min_key = min(self.errors.items(), key=lambda x: x[1])[0]
                del self.errors[min_key]
            
            self.errors[error_msg] = self.errors.get(error_msg, 0) + 1
            if error_context:
                self.recent_errors.append({
                    'timestamp': datetime.now().isoformat(),
                    'message': error_msg,
                    'context': error_context
                })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error statistics and recent errors."""
        with self.lock:
            return {
                'error_counts': dict(self.errors),
                'recent_errors': list(self.recent_errors)
            }

# Global error aggregator
error_aggregator = ErrorAggregator()

class ErrorLoggingFilter(logging.Filter):
    """Filter that forwards error and critical logs to error aggregator."""
    
    def filter(self, record):
        if record.levelno >= logging.ERROR:
            context = {
                'logger': record.name,
                'file': record.filename,
                'line': record.lineno,
                'function': record.funcName
            }
            # Add extra fields if present
            if hasattr(record, 'extra'):
                context.update(record.extra)
            
            error_aggregator.add_error(record.getMessage(), context)
        return True

def setup_logging(log_file: Optional[str] = None, log_level: Optional[str] = None) -> None:
    """
    Set up logging configuration with structured logging and error aggregation.
    
    Args:
        log_file: Optional path to log file. If None, uses the value from config.
        log_level: Optional log level name. If None, uses the value from config.
    """
    log_level = log_level or config.log_level
    log_file = log_file or config.log_file
    
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates when reconfiguring
    for handler in root_logger.handlers[:]:
        handler.close()  # Properly close handlers
        root_logger.removeHandler(handler)
        
    # Add error logging filter to root logger
    error_filter = ErrorLoggingFilter()
    root_logger.addFilter(error_filter)
    
    # Create formatters
    detailed_formatter = StructuredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    console_formatter = StructuredFormatter('%(levelname)s: %(message)s')
    
    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    
    # Set up file handler if log file is specified
    if log_file:
        log_path = Path(log_file)
        
        # Create directory if needed
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set up rotating file handler (512 bytes per file during testing, otherwise 10 MB)
        max_bytes = 512 if log_file and 'test' in log_file else 10*1024*1024
        file_handler = RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)
    
    # Set lower log level for third-party libraries
    logging.getLogger('telethon').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    logging.info(f"Logging configured with level {log_level}")
    if log_file:
        logging.info(f"Log file: {log_file}")

# Set up metrics and statistics tracking
class StatisticsCollector:
    """Enhanced statistics collector for tracking application metrics."""
    
    def __init__(self):
        self.counters = {}
        self.gauges = {}
        self.timers: Dict[str, List[float]] = {}
        self.logger = logging.getLogger('statistics')
        self.lock = threading.Lock()
    
    def increment(self, metric_name: str, value: int = 1):
        """Increment a counter by the specified value."""
        with self.lock:
            if metric_name not in self.counters:
                self.counters[metric_name] = 0
            self.counters[metric_name] += value
    
    def set_gauge(self, metric_name: str, value: float):
        """Set a gauge value (for current state metrics)."""
        with self.lock:
            self.gauges[metric_name] = value
    
    def record_time(self, metric_name: str, duration_ms: float):
        """Record a timing measurement."""
        with self.lock:
            if metric_name not in self.timers:
                self.timers[metric_name] = []
            self.timers[metric_name].append(duration_ms)
            # Keep only last 1000 measurements
            if len(self.timers[metric_name]) > 1000:
                self.timers[metric_name] = self.timers[metric_name][-1000:]
    
    def get_timer_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a timer."""
        with self.lock:
            if metric_name not in self.timers or not self.timers[metric_name]:
                return {}
            
            values = self.timers[metric_name]
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values)
            }
    
    def log_statistics(self):
        """Log all current statistics."""
        with self.lock:
            self.logger.info("Current statistics:")
            
            if self.counters:
                self.logger.info("Counters:")
                for metric, value in sorted(self.counters.items()):
                    self.logger.info(f"  {metric}: {value}")
            
            if self.gauges:
                self.logger.info("Gauges:")
                for metric, value in sorted(self.gauges.items()):
                    self.logger.info(f"  {metric}: {value}")
            
            if self.timers:
                self.logger.info("Timers:")
                for metric in sorted(self.timers.keys()):
                    stats = self.get_timer_stats(metric)
                    if stats:
                        self.logger.info(f"  {metric}:")
                        for stat, value in stats.items():
                            self.logger.info(f"    {stat}: {value:.2f}")

# Create global statistics collector
stats = StatisticsCollector()
