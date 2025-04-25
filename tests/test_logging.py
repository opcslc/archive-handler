import unittest
import logging
import json
import os
import tempfile
from pathlib import Path
from telegram_archive_explorer.logging_setup import setup_logging, StatisticsCollector, stats

class TestLogging(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test.log")
        
    def tearDown(self):
        # Clean up temp files
        for file in Path(self.temp_dir).glob("*"):
            file.unlink()
        os.rmdir(self.temp_dir)
        
    def test_log_levels(self):
        """Test that different log levels work correctly."""
        setup_logging(self.log_file, "DEBUG")
        logger = logging.getLogger("test_logger")
        
        test_messages = {
            "debug": "Debug message",
            "info": "Info message",
            "warning": "Warning message",
            "error": "Error message",
            "critical": "Critical message"
        }
        
        # Log messages at different levels
        logger.debug(test_messages["debug"])
        logger.info(test_messages["info"])
        logger.warning(test_messages["warning"])
        logger.error(test_messages["error"])
        logger.critical(test_messages["critical"])
        
        # Read log file and verify
        with open(self.log_file, 'r') as f:
            log_content = f.read()
            for level, message in test_messages.items():
                # Each log entry is on a new line, check each line for the message
                for line in log_content.splitlines():
                    base_content = line.split(" | ")[0]
                    if message in base_content:
                        break
                else:
                    self.fail(f"Failed to find {message} in log content")
                
    def test_log_rotation(self):
        """Test that log rotation works correctly."""
        max_bytes = 512  # Very small size for testing
        setup_logging(self.log_file, "DEBUG")
        logger = logging.getLogger("test_logger")
        
        # Write enough data to trigger rotation
        large_msg = "x" * 400  # Larger message size
        for _ in range(20):  # More iterations
            logger.info(large_msg)
            
        # Check that rotation occurred
        log_files = list(Path(self.temp_dir).glob("test.log*"))
        self.assertGreater(len(log_files), 1, "Log rotation did not occur as expected")
        
    def test_structured_logging(self):
        """Test structured logging with extra fields."""
        setup_logging(self.log_file, "INFO")
        logger = logging.getLogger("test_logger")
        
        # Log with extra context
        extra = {
            'operation': 'test_op',
            'duration_ms': 150,
            'status': 'success'
        }
        logger.info("Operation completed", extra=extra)
        
        # Verify log contains structured data
        with open(self.log_file, 'r') as f:
            log_content = f.read()
            for key, value in extra.items():
                self.assertIn(str(value), log_content)
                
    def test_statistics_collector(self):
        """Test the statistics collection functionality."""
        stats.counters.clear()  # Reset stats
        
        # Test increment and multiple metrics
        stats.increment("files_processed")
        stats.increment("records_imported", 5)
        stats.increment("files_processed")
        
        self.assertEqual(stats.counters["files_processed"], 2)
        self.assertEqual(stats.counters["records_imported"], 5)
        
        # Test logging of statistics
        setup_logging(self.log_file, "INFO")
        stats.log_statistics()
        
        with open(self.log_file, 'r') as f:
            log_content = f.read()
            # Check each line for the metrics
            found_metrics = []
            for line in log_content.splitlines():
                # Check if this line contains any metrics
                if "statistics" in line:
                    base_content = line.split(" | ")[0]
                    if "files_processed: 2" in base_content:
                        found_metrics.append("files_processed")
                    if "records_imported: 5" in base_content:
                        found_metrics.append("records_imported")
            
            self.assertIn("files_processed", found_metrics, "files_processed metric not found")
            self.assertIn("records_imported: 5", log_content)

if __name__ == '__main__':
    unittest.main()
