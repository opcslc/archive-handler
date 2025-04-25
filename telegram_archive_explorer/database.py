"""
Database module for Telegram Archive Explorer.

This module provides the database connection, session management, and model definitions
using SQLAlchemy ORM. It supports encrypted SQLite databases using SQLCipher.
"""

import logging
import os
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, ForeignKey, 
    Table, Boolean, Index, Text, CheckConstraint, JSON
)

from sqlalchemy.types import TypeDecorator, JSON as SQLAlchemyJSON

# Type aliases for clarity
class JSONType(TypeDecorator):
    """Custom type for JSON columns with proper type hints."""
    impl = SQLAlchemyJSON
    
    def process_bind_param(self, value: Optional[Dict[str, Any]], dialect: Any) -> Optional[Dict[str, Any]]:
        return value
    
    def process_result_value(self, value: Optional[Dict[str, Any]], dialect: Any) -> Optional[Dict[str, Any]]:
        return value
from sqlalchemy.orm import (
    declarative_base, declarative_mixin,
    sessionmaker, relationship, Session, scoped_session
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import SingletonThreadPool

from .config import config, DatabaseConfig
from .logging_setup import stats

logger = logging.getLogger(__name__)

@declarative_mixin
class BaseMixin:
    """Base mixin for all models."""
    pass

Base = declarative_base(cls=BaseMixin, type_annotation_map={Dict[str, Any]: JSONType})

# Association table for many-to-many relationship between URLs and credentials
url_credential_association = Table(
    'url_credential_association', 
    Base.metadata,
    Column('url_id', Integer, ForeignKey('urls.id')),
    Column('credential_id', Integer, ForeignKey('credentials.id'))
)

class Source(Base):  # type: ignore
    """Model for tracking the source of data."""
    __tablename__ = 'sources'
    
    id = Column(Integer, primary_key=True)
    telegram_channel = Column(String(255), nullable=True)
    message_id = Column(Integer, nullable=True)
    file_name = Column(String(255), nullable=True)
    collected_date = Column(DateTime, default=datetime.utcnow)
    import_date = Column(DateTime, default=datetime.utcnow)
    import_batch_id = Column(String(36), nullable=True)  # UUID for batch tracking
    metadata = Column(JSONType, nullable=True)  # For flexible metadata storage
    
    # Relationships
    urls = relationship("URL", back_populates="source")
    credentials = relationship("Credential", back_populates="source")
    
    def __repr__(self):
        return f"<Source(channel='{self.telegram_channel}', file='{self.file_name}')>"

class URL(Base):  # type: ignore
    """Model for URLs found in data dumps."""
    __tablename__ = 'urls'
    
    id = Column(Integer, primary_key=True)
    url = Column(String(2048), nullable=False)
    domain = Column(String(255), nullable=False)  # Made non-nullable
    scheme = Column(String(10), nullable=False, default='https')  # Store protocol separately
    path = Column(Text, nullable=True)  # Store path separately for better pattern matching
    source_id = Column(Integer, ForeignKey('sources.id'))
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_valid = Column(Boolean, default=True)  # Flag for marking invalid URLs
    
    # Relationships
    source = relationship("Source", back_populates="urls")
    credentials = relationship(
        "Credential", 
        secondary=url_credential_association,
        back_populates="urls"
    )
    
    # Indexes and constraints
    __table_args__ = (
        # Basic indexes
        Index('idx_url', 'url'),
        Index('idx_domain', 'domain'),
        # Combined indexes for common queries
        Index('idx_domain_path', 'domain', 'path'),
        Index('idx_scheme_domain', 'scheme', 'domain'),
        # Partial index for valid URLs
        Index('idx_valid_urls', 'url', 'domain', postgresql_where=is_valid),
    )
    
    def __init__(self, *args, **kwargs):
        if 'url' in kwargs:
            from urllib.parse import urlparse
            parsed = urlparse(kwargs['url'])
            kwargs['scheme'] = parsed.scheme or 'https'
            kwargs['domain'] = parsed.netloc.lower()
            kwargs['path'] = parsed.path
        super().__init__(*args, **kwargs)
    
    def __repr__(self):
        return f"<URL(url='{self.url}')>"

class Credential(Base):  # type: ignore
    """Model for credentials (username/email and password)."""
    __tablename__ = 'credentials'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    source_id = Column(Integer, ForeignKey('sources.id'))
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_valid = Column(Boolean, default=True)  # Flag for marking invalid/malformed credentials
    hash_value = Column(String(64))  # Hash of combined fields for duplicate detection
    
    # Relationships
    source = relationship("Source", back_populates="credentials")
    urls = relationship(
        "URL", 
        secondary=url_credential_association,
        back_populates="credentials"
    )
    
    # Indexes and constraints
    __table_args__ = (
        # Basic field indexes
        Index('idx_username', 'username'),
        Index('idx_email', 'email'),
        Index('idx_password', 'password'),
        # Combined indexes for efficient searching
        Index('idx_username_email', 'username', 'email'),
        Index('idx_hash', 'hash_value'),
        # Check constraint to ensure at least username or email is present
        CheckConstraint('username IS NOT NULL OR email IS NOT NULL', name='check_user_identifier'),
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_hash()
    
    def _update_hash(self):
        """Update hash value for duplicate detection."""
        import hashlib
        fields = [
            str(self.username or ''),
            str(self.email or ''),
            str(self.password or '')
        ]
        combined = '|'.join(fields).encode('utf-8')
        self.hash_value = hashlib.sha256(combined).hexdigest()
    
    def __repr__(self):
        if self.email:
            user = self.email
        else:
            user = self.username
        return f"<Credential(user='{user}', password='***')>"

class ImportLog(Base):  # type: ignore
    """Model for tracking import operations and their statistics."""
    __tablename__ = 'import_logs'
    
    id = Column(Integer, primary_key=True)
    batch_id = Column(String(36), nullable=False, index=True)  # UUID for batch tracking
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    total_records = Column(Integer, default=0)
    imported_records = Column(Integer, default=0)
    duplicate_records = Column(Integer, default=0)
    error_records = Column(Integer, default=0)
    skipped_records = Column(Integer, default=0)
    source_id = Column(Integer, ForeignKey('sources.id'))
    
    # Statistics and metadata
    error_details = Column(JSONType, nullable=True)  # Store error messages and counts
    skipped_details = Column(JSONType, nullable=True)  # Store skip reasons and counts
    metadata = Column(JSONType, nullable=True)  # Additional import metadata
    
    # Relationships
    source = relationship("Source", backref="import_logs")
    
    def __repr__(self):
        return f"<ImportLog(batch='{self.batch_id}', imported={self.imported_records}, errors={self.error_records})>"

class Database:
    """Database manager class."""
    
    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        """
        Initialize database connection.
        
        Args:
            db_config: Optional database configuration.
                       If None, uses the configuration from the config module.
        """
        self.db_config = db_config or config.database
        self.engine = None
        self.Session = None
        self._setup_database()
    
    def _setup_database(self):
        """Set up database connection and create tables if they don't exist."""
        db_path = Path(self.db_config.path)
        
        # Create parent directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize engine based on whether encryption is enabled
        if self.db_config.encryption_key:
            # For SQLCipher (encrypted SQLite)
            try:
                # Import pysqlcipher3 only when encryption is enabled
                from pysqlcipher3 import dbapi2 as sqlcipher
                
                # SQLCipher connection string
                uri = f"sqlite:///{db_path}"
                
                # Create engine with custom connect arguments for encryption
                self.engine = create_engine(
                    uri,
                    module=sqlcipher,
                    connect_args={
                        "check_same_thread": False,
                        "uri": True,
                    },
                    poolclass=SingletonThreadPool
                )
                
                # Set up encryption key for each connection
                @event.listens_for(self.engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    cursor.execute(f"PRAGMA key = '{self.db_config.encryption_key}'")
                    cursor.execute("PRAGMA cipher_compatibility = 3")
                    cursor.close()
                
                logger.info("Database initialized with encryption enabled")
            except ImportError:
                logger.error("pysqlcipher3 not installed but encryption requested. Falling back to unencrypted database.")
                self.engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        else:
            # Standard SQLite without encryption
            self.engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
            logger.info("Database initialized without encryption")
        
        # Create session factory
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        
        # Create tables
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get a database session."""
        if not self.Session:
            raise RuntimeError("Database not initialized")
        return self.Session()
    
    def close(self):
        """Close database connection."""
        if self.Session:
            self.Session.remove()
        if self.engine:
            self.engine.dispose()

# Global database instance
db = Database()

def init_db(db_config: Optional[DatabaseConfig] = None):
    """
    Initialize the database.
    
    Args:
        db_config: Optional database configuration.
                   If None, uses the configuration from the config module.
    """
    global db
    db = Database(db_config)
    return db
