import os
import io
import pytest
import tempfile
import zipfile
import tarfile
from pathlib import Path
from telegram_archive_explorer.archive_extractor import (
    ArchiveExtractor, 
    PasswordRequiredError,
    UnsupportedArchiveError
)

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def archive_extractor(temp_dir):
    return ArchiveExtractor(temp_dir=temp_dir)

@pytest.fixture
def sample_zip(temp_dir):
    zip_path = temp_dir / "test.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.txt", "test content")
    return zip_path

@pytest.fixture
def password_protected_zip(temp_dir):
    zip_path = temp_dir / "protected.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.setpassword(b"password123")
        zf.writestr("secret.txt", "secret content")
    return zip_path

@pytest.fixture
def sample_tar(temp_dir):
    tar_path = temp_dir / "test.tar.gz"
    with tarfile.open(tar_path, 'w:gz') as tf:
        data = "test content".encode('utf-8')
        info = tarfile.TarInfo(name="test.txt")
        info.size = len(data)
        tf.addfile(info, fileobj=io.BytesIO(data))
    return tar_path

def test_detect_archive_type(archive_extractor, sample_zip, sample_tar):
    assert archive_extractor.detect_archive_type(sample_zip) == 'zip'
    assert archive_extractor.detect_archive_type(sample_tar) == 'tar_gzip'
    
    with pytest.raises(UnsupportedArchiveError):
        archive_extractor.detect_archive_type(Path("invalid.xyz"))

def test_extract_zip(archive_extractor, sample_zip, temp_dir):
    result = archive_extractor.extract(sample_zip)
    assert result['success']
    assert len(result['extracted_files']) == 1
    assert (result['extracted_path'] / "test.txt").exists()
    with open(result['extracted_files'][0], 'r') as f:
        assert f.read() == "test content"

def test_password_protected_zip(archive_extractor, password_protected_zip):
    # Test without password
    result = archive_extractor.extract(password_protected_zip)
    assert not result['success']
    assert result['password_required']
    
    # Test with correct password
    result = archive_extractor.extract_with_password(password_protected_zip, "password123")
    assert result['success']
    assert len(result['extracted_files']) == 1
    with open(result['extracted_files'][0], 'r') as f:
        assert f.read() == "secret content"

def test_extract_tar(archive_extractor, sample_tar):
    result = archive_extractor.extract(sample_tar)
    assert result['success']
    assert len(result['extracted_files']) == 1
    with open(result['extracted_files'][0], 'r') as f:
        assert f.read() == "test content"

def test_cleanup(archive_extractor, sample_zip, temp_dir):
    # Extract files
    result = archive_extractor.extract(sample_zip)
    extract_path = result['extracted_path']
    assert extract_path.exists()
    
    # Clean specific path
    archive_extractor.cleanup(extract_path)
    assert not extract_path.exists()
    
    # Test cleanup of all temporary files
    result = archive_extractor.extract(sample_zip)
    assert result['extracted_path'].exists()
    archive_extractor.cleanup()
    assert not result['extracted_path'].exists()

def test_password_queue(archive_extractor, password_protected_zip):
    # Extract without password should queue it
    result = archive_extractor.extract(password_protected_zip)
    assert result['password_required']
    
    queue = archive_extractor.get_password_queue()
    assert len(queue) == 1
    assert queue[0]['path'] == str(password_protected_zip)
    assert queue[0]['attempts'] == 0
    
    # Extract with password should remove from queue
    result = archive_extractor.extract_with_password(password_protected_zip, "password123")
    assert result['success']
    
    queue = archive_extractor.get_password_queue()
    assert len(queue) == 0

