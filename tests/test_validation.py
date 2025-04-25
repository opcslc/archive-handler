import pytest
from telegram_archive_explorer.data_parser import DataParser, ValidationError
from telegram_archive_explorer.search import SearchEngine

def test_url_validation():
    """Test URL validation with various patterns"""
    parser = DataParser()
    
    # Valid URLs
    valid_urls = [
        "http://example.com",
        "https://sub.example.com/path",
        "https://example.com:8080",
        "http://example.com/path?param=value",
        "https://user:pass@example.com",
    ]
    for url in valid_urls:
        assert parser.validate_url(url)
    
    # Invalid URLs
    invalid_urls = [
        "not_a_url",
        "http:/example.com",  # Missing slash
        "http://",  # No domain
        "http://.com",  # No domain
        "",  # Empty
    ]
    for url in invalid_urls:
        with pytest.raises(ValidationError):
            parser.validate_url(url)

def test_email_username_validation():
    """Test email and username validation"""
    parser = DataParser()
    
    # Valid emails/usernames
    valid_values = [
        "user@example.com",
        "user.name@sub.example.com",
        "user+tag@example.com",
        "user_name",  # Allow simple usernames
        "user123",
    ]
    for value in valid_values:
        assert parser.validate_username(value)
    
    # Invalid emails/usernames
    invalid_values = [
        "@example.com",  # No user part
        "user@",  # No domain
        "user space@example.com",  # Space in email
        "",  # Empty
        "a" * 256,  # Too long
    ]
    for value in invalid_values:
        with pytest.raises(ValidationError):
            parser.validate_username(value)

def test_password_validation():
    """Test password validation and normalization"""
    parser = DataParser()
    
    # Valid passwords
    valid_passwords = [
        "password123",
        "Pass@word123",
        "very-long-password-123",
        "short",  # Allow short passwords in data
    ]
    for password in valid_passwords:
        assert parser.validate_password(password)
    
    # Invalid passwords
    invalid_passwords = [
        "",  # Empty
        "\n",  # Newline
        "a" * 1000,  # Too long
    ]
    for password in invalid_passwords:
        with pytest.raises(ValidationError):
            parser.validate_password(password)

def test_wildcard_pattern_matching(search_engine, test_db):
    """Test wildcard pattern matching in searches"""
    # Setup test data
    test_data = [
        ("http://example.com", "user1@example.com", "pass1"),
        ("https://test.com", "user2@test.com", "pass2"),
        ("http://sample.net", "admin@sample.net", "pass3"),
    ]
    for url, username, password in test_data:
        search_engine.add_record(url, username, password)
    
    # Test URL wildcards
    assert len(search_engine.search_by_url("*.com")) == 2
    assert len(search_engine.search_by_url("http://*")) == 2
    assert len(search_engine.search_by_url("https://*")) == 1
    
    # Test email/username wildcards
    assert len(search_engine.search_by_username("*@*.com")) == 2
    assert len(search_engine.search_by_username("admin@*")) == 1
    assert len(search_engine.search_by_username("user*")) == 2

def test_data_normalization():
    """Test data normalization functions"""
    parser = DataParser()
    
    # URL normalization
    assert parser.normalize_url("HTTP://EXAMPLE.COM") == "http://example.com"
    assert parser.normalize_url("http://example.com/") == "http://example.com"
    assert parser.normalize_url("example.com") == "http://example.com"
    
    # Username/email normalization
    assert parser.normalize_username("User@Example.COM") == "user@example.com"
    assert parser.normalize_username(" user ") == "user"
    assert parser.normalize_username("USER123") == "user123"
    
    # Password normalization (should preserve case but trim whitespace)
    assert parser.normalize_password(" Password123 ") == "Password123"
    assert parser.normalize_password("Pass  word") == "Pass word"

def test_malformed_data_handling():
    """Test handling of malformed data during parsing"""
    parser = DataParser()
    
    # Test partial data
    partial_data = [
        "http://example.com,user@example.com",  # Missing password
        "http://example.com,,pass123",  # Missing username
        ",user@example.com,pass123",  # Missing URL
    ]
    
    for line in partial_data:
        result = parser.parse_line(line)
        assert result['is_valid'] is False
        assert 'error' in result
    
    # Test completely malformed data
    malformed_data = [
        "",  # Empty line
        "single_column",  # Too few columns
        "a,b,c,d,e",  # Too many columns
        "\n,\n,\n",  # Only newlines
    ]
    
    for line in malformed_data:
        result = parser.parse_line(line)
        assert result['is_valid'] is False
        assert 'error' in result

def test_encoding_handling():
    """Test handling of different text encodings"""
    parser = DataParser()
    
    # Test UTF-8 data
    utf8_data = "http://ünicode.com,üser@example.com,päassword123"
    result = parser.parse_line(utf8_data)
    assert result['is_valid']
    assert 'ünicode.com' in result['url']
    
    # Test ASCII data
    ascii_data = "http://ascii.com,user@ascii.com,password123"
    result = parser.parse_line(ascii_data)
    assert result['is_valid']
    
    # Test handling of invalid UTF-8
    invalid_utf8 = b"http://example.com,user@example.com,pass123\xFF".decode('utf-8', 'ignore')
    result = parser.parse_line(invalid_utf8)
    assert result['is_valid']  # Should handle gracefully after ignore
