import os
import pytest
from pathlib import Path
from telegram_archive_explorer.telegram_client import TelegramClient
from telegram_archive_explorer.archive_extractor import ArchiveExtractor
from telegram_archive_explorer.data_parser import DataParser
from telegram_archive_explorer.data_importer import DataImporter
from telegram_archive_explorer.search import SearchEngine

@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test complete workflow from download to search"""
    
    @pytest.fixture(autouse=True)
    def setup(self, temp_dir, test_db, test_config, mock_telegram_client):
        self.temp_dir = temp_dir
        self.db = test_db
        self.config = test_config
        self.telegram_client = mock_telegram_client
        
        # Set up mock response for telegram client
        self.telegram_client.download_archive.return_value = {
            'path': temp_dir / 'test_archive.zip',
            'message_id': 123,
            'channel_id': 456
        }
        
        # Create components
        self.extractor = ArchiveExtractor(temp_dir=temp_dir)
        self.parser = DataParser()
        self.importer = DataImporter(session=test_db)
        self.search = SearchEngine(session=test_db)
        
        # Create test archive with sample data
        self._create_test_archive()
    
    def _create_test_archive(self):
        """Create a test archive with sample data"""
        archive_dir = self.temp_dir / 'archive_contents'
        archive_dir.mkdir(exist_ok=True)
        
        # Create sample data file
        data_file = archive_dir / 'data.txt'
        with open(data_file, 'w') as f:
            f.write("http://site1.com,user1@site1.com,pass1\n")
            f.write("http://site2.com,user2@site2.com,pass2\n")
        
        # Create zip archive
        import zipfile
        archive_path = self.temp_dir / 'test_archive.zip'
        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.write(data_file, data_file.name)
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow from download to search"""
        # 1. Download archive from Telegram
        download_result = await self.telegram_client.download_archive('@test_channel')
        assert download_result['path'].exists()
        
        # 2. Extract archive
        extract_result = self.extractor.extract(download_result['path'])
        assert extract_result['success']
        assert len(extract_result['files']) > 0
        
        # 3. Parse and import data
        for file_path in extract_result['files']:
            with open(file_path) as f:
                for line in f:
                    parsed = self.parser.parse_line(line.strip())
                    if parsed['is_valid']:
                        self.importer.import_record(
                            url=parsed['url'],
                            username=parsed['username'],
                            password=parsed['password'],
                            source_info={
                                'channel_id': download_result['channel_id'],
                                'message_id': download_result['message_id'],
                                'file': file_path.name
                            }
                        )
        
        # 4. Verify search functionality
        # Search by URL
        url_results = list(self.search.search_by_url("site1.com"))
        assert len(url_results) == 1
        assert url_results[0].url == "http://site1.com"
        
        # Search by username
        user_results = list(self.search.search_by_username("user2"))
        assert len(user_results) == 1
        assert user_results[0].username == "user2@site2.com"
        
        # Verify source tracking
        assert url_results[0].source_info['channel_id'] == 456
        assert url_results[0].source_info['message_id'] == 123
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """Test error handling throughout the workflow"""
        # 1. Test network error handling
        self.telegram_client.download_archive.side_effect = Exception("Network error")
        with pytest.raises(Exception):
            await self.telegram_client.download_archive('@test_channel')
        
        # 2. Test corrupt archive handling
        with open(self.temp_dir / 'corrupt.zip', 'w') as f:
            f.write("Not a zip file")
        with pytest.raises(Exception):
            self.extractor.extract(self.temp_dir / 'corrupt.zip')
        
        # 3. Test malformed data handling
        malformed_data = "not,enough,columns"
        parsed = self.parser.parse_line(malformed_data)
        assert not parsed['is_valid']
        assert 'error' in parsed
    
    def test_duplicate_handling_workflow(self):
        """Test duplicate handling in the workflow"""
        # Import initial data
        self.importer.import_record(
            url="http://example.com",
            username="user@example.com",
            password="pass123",
            source_info={'file': 'test1.txt'}
        )
        
        # Try importing duplicate
        self.importer.import_record(
            url="http://example.com",
            username="user@example.com",
            password="pass123",
            source_info={'file': 'test2.txt'}
        )
        
        # Verify only one record exists
        results = list(self.search.search_by_url("example.com"))
        assert len(results) == 1
        
        # Verify source info was updated
        assert 'test2.txt' in str(results[0].source_info)
    
    def test_cleanup_workflow(self):
        """Test cleanup of temporary files"""
        # 1. Create some temporary files
        test_file = self.temp_dir / 'test.txt'
        test_file.touch()
        
        # 2. Run extraction (which should clean up after itself)
        self.extractor.extract(self.temp_dir / 'test_archive.zip')
        
        # 3. Verify cleanup
        extracted_files = list(self.temp_dir.glob('**/*'))
        # Should only have our test archive and the original test file
        assert len([f for f in extracted_files if f.is_file()]) <= 2

