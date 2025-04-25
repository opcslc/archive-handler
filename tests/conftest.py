import os
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram_archive_explorer.database import Base, init_db
from telegram_archive_explorer.config import Config
from telegram_archive_explorer.telegram_client import TelegramClient
from telegram_archive_explorer.archive_extractor import ArchiveExtractor
from telegram_archive_explorer.data_parser import DataParser
from telegram_archive_explorer.data_importer import DataImporter
from telegram_archive_explorer.search import SearchEngine

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def test_db():
    """Create a test database"""
    db_path = "sqlite:///:memory:"
    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration"""
    config = Config()
    config.telegram_api_id = "test_api_id"
    config.telegram_api_hash = "test_api_hash"
    config.download_dir = temp_dir / "downloads"
    config.extract_dir = temp_dir / "extracted"
    config.db_path = ":memory:"
    return config

@pytest.fixture
def mock_telegram_client(mocker):
    """Create a mocked TelegramClient"""
    client = mocker.Mock(spec=TelegramClient)
    return client

@pytest.fixture
def archive_extractor(temp_dir):
    """Create an ArchiveExtractor instance"""
    return ArchiveExtractor(temp_dir=temp_dir)

@pytest.fixture
def data_parser():
    """Create a DataParser instance"""
    return DataParser()

@pytest.fixture
def data_importer(test_db):
    """Create a DataImporter instance"""
    return DataImporter(session=test_db)

@pytest.fixture
def search_engine(test_db):
    """Create a SearchEngine instance"""
    return SearchEngine(session=test_db)

@pytest.fixture
def large_dataset():
    """Generate a large test dataset"""
    data = []
    for i in range(10000):
        data.append({
            'url': f'http://example{i}.com',
            'username': f'user{i}@example.com',
            'password': f'password{i}'
        })
    return data

@pytest.fixture(autouse=True)
def cleanup_files(temp_dir):
    """Cleanup any files after each test"""
    yield
    for item in temp_dir.glob('**/*'):
        if item.is_file():
            item.unlink()
