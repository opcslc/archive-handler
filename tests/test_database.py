import unittest
from datetime import datetime
from telegram_archive_explorer.database import Database, Source, URL, Credential, db
from telegram_archive_explorer.config import DatabaseConfig

class TestDatabase(unittest.TestCase):
    def setUp(self):
        """Set up test database."""
        self.db_config = DatabaseConfig(path=":memory:")  # Use in-memory SQLite for testing
        self.db = Database(self.db_config)
        self.session = self.db.get_session()

    def tearDown(self):
        """Clean up after tests."""
        self.session.close()
        self.db.close()

    def test_source_creation(self):
        """Test creating a source record."""
        source = Source(
            telegram_channel="test_channel",
            message_id=123,
            file_name="test.txt"
        )
        self.session.add(source)
        self.session.commit()
        
        saved_source = self.session.query(Source).first()
        self.assertEqual(saved_source.telegram_channel, "test_channel")
        self.assertEqual(saved_source.message_id, 123)

    def test_url_creation_and_indexing(self):
        """Test URL creation and relationship with source."""
        source = Source(telegram_channel="test_channel")
        url = URL(
            url="https://example.com",
            domain="example.com",
            source=source
        )
        self.session.add(url)
        self.session.commit()
        
        found_url = self.session.query(URL).filter_by(domain="example.com").first()
        self.assertEqual(found_url.url, "https://example.com")
        self.assertEqual(found_url.source.telegram_channel, "test_channel")

    def test_credential_creation(self):
        """Test credential creation and relationships."""
        source = Source(telegram_channel="test_channel")
        url = URL(url="https://example.com", source=source)
        cred = Credential(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            source=source
        )
        cred.urls.append(url)
        
        self.session.add(cred)
        self.session.commit()
        
        found_cred = self.session.query(Credential).filter_by(email="test@example.com").first()
        self.assertEqual(found_cred.username, "testuser")
        self.assertEqual(len(found_cred.urls), 1)
        self.assertEqual(found_cred.urls[0].url, "https://example.com")

    def test_duplicate_handling(self):
        """Test handling of duplicate records with partial matches."""
        # Create initial record
        source1 = Source(telegram_channel="channel1")
        url1 = URL(url="https://example.com", source=source1)
        cred1 = Credential(
            username="user1",
            password="pass123",
            source=source1
        )
        cred1.urls.append(url1)
        self.session.add(cred1)
        self.session.commit()
        
        # Create partial match (same URL, different credentials)
        source2 = Source(telegram_channel="channel2")
        url2 = URL(url="https://example.com", source=source2)
        cred2 = Credential(
            username="user2",
            password="pass456",
            source=source2
        )
        cred2.urls.append(url2)
        self.session.add(cred2)
        self.session.commit()
        
        url_records = self.session.query(URL).filter_by(url="https://example.com").all()
        self.assertEqual(len(url_records), 2)
        
        credentials = self.session.query(Credential).all()
        self.assertEqual(len(credentials), 2)

    def test_large_dataset_performance(self):
        """Test database performance with larger datasets."""
        batch_size = 1000
        for i in range(batch_size):
            source = Source(telegram_channel=f"channel_{i}")
            url = URL(
                url=f"https://example{i}.com",
                domain=f"example{i}.com",
                source=source
            )
            cred = Credential(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password=f"pass{i}",
                source=source
            )
            cred.urls.append(url)
            self.session.add(cred)
            
            if i % 100 == 0:
                self.session.commit()
        
        self.session.commit()
        
        url_count = self.session.query(URL).count()
        cred_count = self.session.query(Credential).count()
        self.assertEqual(url_count, batch_size)
        self.assertEqual(cred_count, batch_size)

if __name__ == '__main__':
    unittest.main()
