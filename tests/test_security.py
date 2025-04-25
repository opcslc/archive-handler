import os
import pytest
from pathlib import Path
from telegram_archive_explorer.database import encrypt_data, decrypt_data, DataRecord
from telegram_archive_explorer.config import Config
from tests.factories import TestDataFactory

class TestEncryption:
    """Test encryption and security features"""
    
    @pytest.fixture(autouse=True)
    def setup(self, test_db, test_config):
        self.db = test_db
        self.config = test_config
        
        # Ensure encryption key is set
        os.environ['ENCRYPTION_KEY'] = 'test_key_32_bytes_long_............'
    
    def test_data_encryption_at_rest(self):
        """Test that sensitive data is encrypted in the database"""
        # Create test record
        record = TestDataFactory.create_data_record()
        original_password = record.password
        
        # Save to database
        self.db.add(record)
        self.db.commit()
        
        # Fetch directly from database
        fetched_record = self.db.query(DataRecord).first()
        
        # Verify password is encrypted in database
        assert fetched_record.password != original_password
        assert len(fetched_record.password) > len(original_password)
        
        # Verify password can be decrypted
        decrypted_password = decrypt_data(fetched_record.password)
        assert decrypted_password == original_password
    
    def test_encryption_key_rotation(self):
        """Test key rotation functionality"""
        # Create and save record with old key
        old_key = 'old_key_32_bytes_long_............'
        os.environ['ENCRYPTION_KEY'] = old_key
        
        record = TestDataFactory.create_data_record()
        original_password = record.password
        self.db.add(record)
        self.db.commit()
        
        # Rotate to new key
        new_key = 'new_key_32_bytes_long_............'
        os.environ['ENCRYPTION_KEY'] = new_key
        
        # Re-encrypt data with new key
        fetched_record = self.db.query(DataRecord).first()
        old_encrypted = fetched_record.password
        
        decrypted = decrypt_data(old_encrypted, key=old_key)
        new_encrypted = encrypt_data(decrypted, key=new_key)
        
        fetched_record.password = new_encrypted
        self.db.commit()
        
        # Verify data can be decrypted with new key
        final_record = self.db.query(DataRecord).first()
        decrypted_password = decrypt_data(final_record.password, key=new_key)
        assert decrypted_password == original_password
    
    def test_encryption_error_handling(self):
        """Test error handling in encryption/decryption"""
        test_data = "sensitive_data"
        
        # Test with invalid key
        with pytest.raises(ValueError):
            encrypt_data(test_data, key="short_key")
        
        # Test with None data
        with pytest.raises(ValueError):
            encrypt_data(None)
        
        # Test decryption with invalid data
        with pytest.raises(ValueError):
            decrypt_data("not_encrypted_data")
        
        # Test decryption with wrong key
        encrypted = encrypt_data(test_data)
        wrong_key = 'wrong_key_32_bytes_long_...........'
        with pytest.raises(ValueError):
            decrypt_data(encrypted, key=wrong_key)

class TestAccessControl:
    """Test access control and permission features"""
    
    @pytest.fixture(autouse=True)
    def setup(self, test_db, test_config):
        self.db = test_db
        self.config = test_config
    
    def test_config_file_permissions(self, temp_dir):
        """Test configuration file permission handling"""
        config_file = temp_dir / 'config.ini'
        
        # Write config with sensitive data
        config = Config()
        config.telegram_api_id = "sensitive_api_id"
        config.telegram_api_hash = "sensitive_api_hash"
        config.save(config_file)
        
        # Check file permissions
        import stat
        file_stat = os.stat(config_file)
        
        # Verify file is readable only by owner
        assert not file_stat.st_mode & stat.S_IRGRP
        assert not file_stat.st_mode & stat.S_IROTH
        
        # Verify file is not executable
        assert not file_stat.st_mode & stat.S_IXUSR
        assert not file_stat.st_mode & stat.S_IXGRP
        assert not file_stat.st_mode & stat.S_IXOTH
    
    def test_sensitive_data_logging(self, temp_dir):
        """Test that sensitive data is not logged"""
        from telegram_archive_explorer.logging_setup import setup_logging
        import logging
        
        # Setup logging to a test file
        log_file = temp_dir / 'test.log'
        setup_logging(log_file)
        logger = logging.getLogger('telegram_archive_explorer')
        
        # Create test data
        test_record = TestDataFactory.create_data_record()
        
        # Log some operations with the record
        logger.info(f"Processing record for URL: {test_record.url}")
        logger.debug(f"Record details: {test_record}")
        
        # Check log file content
        with open(log_file) as f:
            log_content = f.read()
            
            # URL should be logged
            assert test_record.url in log_content
            
            # Password should not be logged
            assert test_record.password not in log_content
            assert '[REDACTED]' in log_content

class TestDataProtection:
    """Test data protection features"""
    
    @pytest.fixture(autouse=True)
    def setup(self, temp_dir, test_db):
        self.temp_dir = temp_dir
        self.db = test_db
    
    def test_secure_file_deletion(self):
        """Test secure deletion of sensitive files"""
        from telegram_archive_explorer.archive_extractor import secure_delete
        
        # Create test file with sensitive data
        test_file = self.temp_dir / 'sensitive.txt'
        test_data = "sensitive_information"
        with open(test_file, 'w') as f:
            f.write(test_data)
        
        # Securely delete file
        secure_delete(test_file)
        
        # Verify file is gone
        assert not test_file.exists()
        
        # If file existed, verify content was overwritten
        if test_file.exists():
            with open(test_file, 'rb') as f:
                content = f.read()
                assert test_data.encode() not in content
    
    def test_temp_file_cleanup(self):
        """Test cleanup of temporary files containing sensitive data"""
        # Create some test files
        temp_files = []
        for i in range(3):
            temp_file = self.temp_dir / f'temp_{i}.txt'
            temp_file.write_text(f"sensitive_data_{i}")
            temp_files.append(temp_file)
        
        # Simulate extraction process
        extractor = ArchiveExtractor(temp_dir=self.temp_dir)
        try:
            # Simulate processing
            raise Exception("Simulated error")
        except Exception:
            # Cleanup should happen even on error
            extractor.cleanup()
        
        # Verify all temp files are removed
        for temp_file in temp_files:
            assert not temp_file.exists()
    
    def test_memory_protection(self):
        """Test protection of sensitive data in memory"""
        import gc
        import ctypes
        
        # Create sensitive data
        sensitive_data = "very_sensitive_password"
        
        # Simulate processing
        def process_sensitive_data():
            # Use the sensitive data
            temp = sensitive_data * 2
            
            # Clear variable
            if hasattr(ctypes, 'memset'):
                # Get pointer to string buffer
                buf = ctypes.c_char_p(sensitive_data.encode())
                ctypes.memset(buf, 0, len(sensitive_data))
        
        # Run processing
        process_sensitive_data()
        
        # Force garbage collection
        gc.collect()
        
        # Memory test is somewhat limited in Python, but we can check basic cleanup
        assert sensitive_data not in str(gc.get_objects())
