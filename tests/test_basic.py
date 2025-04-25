"""
Basic tests for the Telegram Archive Explorer package.

These tests verify that the package can be imported and basic functionality works.
"""

import os
import sys
import unittest
from pathlib import Path

# Add parent directory to path to import the package
sys.path.insert(0, str(Path(__file__).parent.parent))

import telegram_archive_explorer
from telegram_archive_explorer import config, database, logging_setup
from telegram_archive_explorer.data_parser import DataRecord

class BasicTests(unittest.TestCase):
    """Basic tests for the package."""
    
    def test_import(self):
        """Test that the package can be imported."""
        self.assertIsNotNone(telegram_archive_explorer)
        self.assertIsNotNone(telegram_archive_explorer.__version__)
    
    def test_data_record(self):
        """Test the DataRecord class."""
        # Create a record
        record = DataRecord(
            url="http://example.com",
            username="testuser",
            password="testpass"
        )
        
        # Check attributes
        self.assertEqual(record.url, "http://example.com")
        self.assertEqual(record.username, "testuser")
        self.assertEqual(record.password, "testpass")
        self.assertEqual(record.domain, "example.com")
        
        # Test normalization
        record2 = DataRecord(
            url="example.com",  # Missing scheme
            username=" user ",  # Extra whitespace
            password="pass"
        )
        
        self.assertEqual(record2.url, "http://example.com")
        self.assertEqual(record2.username, "user")
        
        # Test email normalization
        record3 = DataRecord(
            email="TEST@EXAMPLE.COM",  # Should be lowercased
            password="pass"
        )
        
        self.assertEqual(record3.email, "test@example.com")
        
        # Test validity
        self.assertTrue(record.is_valid())
        self.assertTrue(record.is_complete())
        
        # Empty record should not be valid
        empty_record = DataRecord()
        self.assertFalse(empty_record.is_valid())
        self.assertFalse(empty_record.is_complete())

if __name__ == '__main__':
    unittest.main()
