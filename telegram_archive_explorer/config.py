"""
Configuration management for Telegram Archive Explorer.

This module handles loading configuration from files and environment variables,
and provides a central configuration object for the application.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class TelegramConfig:
    """Configuration for Telegram API access."""
    api_id: int
    api_hash: str
    session_name: str = "telegram_archive_explorer"
    
@dataclass
class DatabaseConfig:
    """Configuration for database connection."""
    path: str
    encryption_key: Optional[str] = None
    
    @property
    def uri(self) -> str:
        """Get the database URI."""
        base_uri = f"sqlite:///{self.path}"
        if self.encryption_key:
            # Using SQLCipher for encrypted database
            return f"{base_uri}?cipher=aes-256-cfb&key={self.encryption_key}"
        return base_uri

@dataclass
class AppConfig:
    """Main configuration class for the application."""
    telegram: TelegramConfig
    database: DatabaseConfig
    log_level: str = "INFO"
    log_file: Optional[str] = None
    temp_dir: str = "temp"
    
def get_config_dir() -> Path:
    """Get the configuration directory path."""
    # Use XDG_CONFIG_HOME if available, otherwise use ~/.config
    if os.environ.get("XDG_CONFIG_HOME"):
        config_dir = Path(os.environ["XDG_CONFIG_HOME"]) / "telegram_archive_explorer"
    else:
        config_dir = Path.home() / ".config" / "telegram_archive_explorer"
        
    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def load_config() -> AppConfig:
    """
    Load configuration from config file and environment variables.
    Environment variables take precedence over config file values.
    """
    config_file = get_config_dir() / "config.json"
    
    # Default configuration
    config_data = {
        "telegram": {
            "api_id": None,
            "api_hash": None,
            "session_name": "telegram_archive_explorer"
        },
        "database": {
            "path": str(get_config_dir() / "database.db"),
            "encryption_key": None
        },
        "log_level": "INFO",
        "log_file": str(get_config_dir() / "app.log"),
        "temp_dir": str(get_config_dir() / "temp")
    }
    
    # Load from config file if it exists
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                # Update config with file values
                for section, values in file_config.items():
                    if section in config_data and isinstance(values, dict):
                        config_data[section].update(values)
                    else:
                        config_data[section] = values
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
    
    # Override with environment variables
    env_mapping = {
        "TELEGRAM_API_ID": ("telegram", "api_id", int),
        "TELEGRAM_API_HASH": ("telegram", "api_hash", str),
        "TELEGRAM_SESSION_NAME": ("telegram", "session_name", str),
        "DATABASE_PATH": ("database", "path", str),
        "DATABASE_ENCRYPTION_KEY": ("database", "encryption_key", str),
        "LOG_LEVEL": ("log_level", None, str),
        "LOG_FILE": ("log_file", None, str),
        "TEMP_DIR": ("temp_dir", None, str),
    }
    
    for env_var, (section, key, type_func) in env_mapping.items():
        if env_var in os.environ:
            try:
                value = type_func(os.environ[env_var])
                if key is None:
                    config_data[section] = value
                else:
                    config_data[section][key] = value
            except Exception as e:
                logger.error(f"Failed to parse environment variable {env_var}: {e}")
    
    # Create and return AppConfig instance
    return AppConfig(
        telegram=TelegramConfig(**config_data["telegram"]),
        database=DatabaseConfig(**config_data["database"]),
        log_level=config_data["log_level"],
        log_file=config_data["log_file"],
        temp_dir=config_data["temp_dir"]
    )

# Create global config instance
config = load_config()
