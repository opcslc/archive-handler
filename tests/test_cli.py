import pytest
from click.testing import CliRunner
from telegram_archive_explorer.cli import cli
from tests.factories import TestDataFactory

@pytest.fixture
def runner():
    """Create a CLI runner"""
    return CliRunner()

def test_basic_cli(runner):
    """Test basic CLI functionality"""
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Telegram Archive Explorer' in result.output

def test_version_command(runner):
    """Test version display"""
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert 'version' in result.output.lower()

def test_search_command(runner, test_db):
    """Test search command functionality"""
    # Add test data
    records = TestDataFactory.create_batch(5)
    for record in records:
        test_db.add(record)
    test_db.commit()
    
    # Test URL search
    result = runner.invoke(cli, ['search', '--url', records[0].url])
    assert result.exit_code == 0
    assert records[0].url in result.output
    
    # Test username search
    result = runner.invoke(cli, ['search', '--username', records[0].username])
    assert result.exit_code == 0
    assert records[0].username in result.output
    
    # Test different output formats
    formats = ['table', 'json', 'csv']
    for fmt in formats:
        result = runner.invoke(cli, ['search', '--url', records[0].url, '--format', fmt])
        assert result.exit_code == 0

def test_channel_commands(runner, test_config):
    """Test channel management commands"""
    # Add channel
    result = runner.invoke(cli, ['channels', '--add', '@test_channel'])
    assert result.exit_code == 0
    
    # List channels
    result = runner.invoke(cli, ['channels', '--list'])
    assert result.exit_code == 0
    assert '@test_channel' in result.output
    
    # Remove channel
    result = runner.invoke(cli, ['channels', '--remove', '@test_channel'])
    assert result.exit_code == 0
    
    # Verify removal
    result = runner.invoke(cli, ['channels', '--list'])
    assert result.exit_code == 0
    assert '@test_channel' not in result.output

def test_config_commands(runner, temp_dir):
    """Test configuration commands"""
    # Set API credentials
    result = runner.invoke(cli, [
        'config', 
        '--api-id', '12345', 
        '--api-hash', 'testhash'
    ])
    assert result.exit_code == 0
    
    # Show config
    result = runner.invoke(cli, ['config', '--show'])
    assert result.exit_code == 0
    assert '12345' not in result.output  # Sensitive data should be masked

def test_collect_command(runner, mock_telegram_client):
    """Test archive collection command"""
    # Test manual collection
    result = runner.invoke(cli, ['collect', '--now'])
    assert result.exit_code == 0
    
    # Test schedule setting
    result = runner.invoke(cli, ['collect', '--schedule', '0 */6 * * *'])
    assert result.exit_code == 0
    assert 'Schedule updated' in result.output

def test_error_handling(runner):
    """Test CLI error handling"""
    # Test invalid command
    result = runner.invoke(cli, ['invalid'])
    assert result.exit_code != 0
    assert 'Error' in result.output
    
    # Test missing required arguments
    result = runner.invoke(cli, ['search'])
    assert result.exit_code != 0
    assert 'Error' in result.output
    
    # Test invalid configuration
    result = runner.invoke(cli, ['collect', '--now'], env={'TELEGRAM_API_ID': ''})
    assert result.exit_code != 0
    assert 'API credentials' in result.output

def test_interactive_features(runner):
    """Test interactive CLI features"""
    # Test password prompt
    result = runner.invoke(cli, ['config'], input='secret\nsecret\n')
    assert result.exit_code == 0
    
    # Test confirmation prompt
    result = runner.invoke(cli, ['channels', '--remove', '@test_channel'], input='y\n')
    assert result.exit_code == 0

def test_output_formatting(runner, test_db):
    """Test output formatting options"""
    # Create test data
    records = TestDataFactory.create_batch(3)
    for record in records:
        test_db.add(record)
    test_db.commit()
    
    # Test table format
    result = runner.invoke(cli, ['search', '--url', records[0].url, '--format', 'table'])
    assert result.exit_code == 0
    assert '│' in result.output  # Table borders
    
    # Test JSON format
    result = runner.invoke(cli, ['search', '--url', records[0].url, '--format', 'json'])
    assert result.exit_code == 0
    assert '{' in result.output
    assert '}' in result.output
    
    # Test CSV format
    result = runner.invoke(cli, ['search', '--url', records[0].url, '--format', 'csv'])
    assert result.exit_code == 0
    assert ',' in result.output

def test_progress_feedback(runner, mock_telegram_client):
    """Test progress indication for long operations"""
    # Test collection with progress
    result = runner.invoke(cli, ['collect', '--now', '--verbose'])
    assert result.exit_code == 0
    assert 'Progress' in result.output
    
    # Test search with count
    result = runner.invoke(cli, ['search', '--url', '*', '--count'])
    assert result.exit_code == 0
    assert 'Found' in result.output
