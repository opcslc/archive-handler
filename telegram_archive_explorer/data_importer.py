"""
Database import functionality for parsed data.

This module handles importing parsed data into the database, including
duplicate detection and management.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import db, URL, Credential, Source
from .data_parser import DataRecord
from .logging_setup import stats

logger = logging.getLogger(__name__)

class ImportResult:
    """Class representing the result of an import operation."""
    
    def __init__(self):
        """Initialize import result."""
        self.total_records = 0
        self.imported_records = 0
        self.duplicate_records = 0
        self.error_records = 0
        self.skipped_records = 0
        self.start_time = time.time()
        self.end_time = None
        self.duration = 0
        self.errors = []
    
    def add_error(self, error_message: str):
        """
        Add an error message.
        
        Args:
            error_message: Error message to add
        """
        self.errors.append(error_message)
        self.error_records += 1
    
    def finish(self):
        """Mark the import as finished and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
    
    def __str__(self) -> str:
        """
        String representation of import results.
        
        Returns:
            Formatted string with import statistics
        """
        status = "completed" if self.end_time else "in progress"
        duration = f"{self.duration:.2f} seconds" if self.end_time else "ongoing"
        
        return (
            f"Import {status} in {duration}\n"
            f"Total records: {self.total_records}\n"
            f"Imported: {self.imported_records}\n"
            f"Duplicates: {self.duplicate_records}\n"
            f"Errors: {self.error_records}\n"
            f"Skipped: {self.skipped_records}\n"
        )

class DataImporter:
    """Class for importing parsed data into the database."""
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize the data importer.
        
        Args:
            session: Optional database session.
                    If None, creates a new session.
        """
        self.session = session or db.get_session()
        self.batch_size = 1000  # Number of records to commit at once
        self.url_cache = {}     # Cache to reduce duplicate URL queries
        self.credential_cache = {}  # Cache to reduce duplicate credential queries
    
    def _find_existing_url(self, url: str) -> Optional[URL]:
        """
        Find an existing URL in the database.
        
        Args:
            url: URL to find
            
        Returns:
            URL entity or None if not found
        """
        # Check cache first
        if url in self.url_cache:
            return self.url_cache[url]
            
        # Query database
        existing = self.session.query(URL).filter(URL.url == url).first()
        
        # Update cache
        self.url_cache[url] = existing
        
        return existing
    
    def _find_existing_credential(self, username: Optional[str], email: Optional[str], 
                                 password: str) -> Optional[Credential]:
        """
        Find an existing credential in the database.
        
        Args:
            username: Optional username
            email: Optional email
            password: Password
            
        Returns:
            Credential entity or None if not found
        """
        # Create a cache key
        cache_key = f"{username}:{email}:{password}"
        
        # Check cache first
        if cache_key in self.credential_cache:
            return self.credential_cache[cache_key]
            
        # Build query based on available fields
        query = self.session.query(Credential)
        
        if username:
            query = query.filter(Credential.username == username)
        else:
            query = query.filter(Credential.username == None)
            
        if email:
            query = query.filter(Credential.email == email)
        else:
            query = query.filter(Credential.email == None)
            
        query = query.filter(Credential.password == password)
        
        existing = query.first()
        
        # Update cache
        self.credential_cache[cache_key] = existing
        
        return existing
    
    def _find_partial_credential_match(self, username: Optional[str], email: Optional[str], 
                                      password: str) -> List[Credential]:
        """
        Find credentials that partially match the given criteria.
        
        Args:
            username: Optional username
            email: Optional email
            password: Password
            
        Returns:
            List of matching credential entities
        """
        # Build query based on available fields
        matches = []
        
        # Username + password match
        if username:
            username_matches = (
                self.session.query(Credential)
                .filter(Credential.username == username, 
                        Credential.password == password)
                .all()
            )
            matches.extend(username_matches)
        
        # Email + password match
        if email:
            email_matches = (
                self.session.query(Credential)
                .filter(Credential.email == email, 
                        Credential.password == password)
                .all()
            )
            matches.extend(email_matches)
        
        return matches
    
    def _create_or_update_source(self, source_info: Dict[str, Any]) -> Source:
        """
        Create a new source record or update an existing one.
        
        Args:
            source_info: Dictionary with source information
            
        Returns:
            Source entity
        """
        telegram_channel = source_info.get('telegram_channel')
        message_id = source_info.get('message_id')
        file_name = source_info.get('file_name')
        
        # Try to find an existing source with the same message_id
        if message_id:
            existing = (
                self.session.query(Source)
                .filter(Source.telegram_channel == telegram_channel,
                        Source.message_id == message_id)
                .first()
            )
            
            if existing:
                return existing
        
        # Create a new source
        source = Source(
            telegram_channel=telegram_channel,
            message_id=message_id,
            file_name=file_name,
            collected_date=source_info.get('collected_date', datetime.utcnow())
        )
        
        self.session.add(source)
        return source
    
    def import_record(self, record: DataRecord, source: Source) -> Tuple[bool, str]:
        """
        Import a single data record.
        
        Args:
            record: DataRecord to import
            source: Source entity
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # URL handling
            url_entity = None
            if record.url:
                # Check for existing URL
                url_entity = self._find_existing_url(record.url)
                
                if not url_entity:
                    # Create new URL
                    url_entity = URL(
                        url=record.url,
                        domain=record.domain,
                        source=source
                    )
                    self.session.add(url_entity)
                    self.url_cache[record.url] = url_entity
            
            # Credential handling
            credential_entity = None
            if record.password and (record.username or record.email):
                # Check for existing credential
                credential_entity = self._find_existing_credential(
                    record.username, record.email, record.password
                )
                
                if not credential_entity:
                    # Create new credential
                    credential_entity = Credential(
                        username=record.username,
                        email=record.email,
                        password=record.password,
                        source=source
                    )
                    self.session.add(credential_entity)
                    
                    # Update cache
                    cache_key = f"{record.username}:{record.email}:{record.password}"
                    self.credential_cache[cache_key] = credential_entity
                    
                # Associate URL with credential if both exist
                if url_entity and credential_entity and url_entity not in credential_entity.urls:
                    credential_entity.urls.append(url_entity)
            
            return True, "Record imported successfully"
            
        except Exception as e:
            logger.error(f"Error importing record: {e}")
            return False, f"Error: {str(e)}"
    
    def import_records(self, records: List[DataRecord], 
                      source_info: Dict[str, Any]) -> ImportResult:
        """
        Import a list of data records.
        
        Args:
            records: List of DataRecords to import
            source_info: Dictionary with source information
            
        Returns:
            ImportResult with import statistics
        """
        result = ImportResult()
        result.total_records = len(records)
        
        # Create or update source
        source = self._create_or_update_source(source_info)
        
        # Process records in batches
        batch_count = 0
        
        try:
            for record in records:
                # Skip invalid records
                if not record.is_valid():
                    result.skipped_records += 1
                    continue
                
                success, message = self.import_record(record, source)
                
                if success:
                    result.imported_records += 1
                else:
                    result.add_error(message)
                
                # Commit in batches
                batch_count += 1
                if batch_count >= self.batch_size:
                    self.session.commit()
                    batch_count = 0
                    
                    # Report progress
                    progress = min(100, int((result.imported_records + result.error_records) / result.total_records * 100))
                    logger.info(f"Import progress: {progress}% ({result.imported_records} imported, {result.error_records} errors)")
            
            # Final commit for any remaining records
            if batch_count > 0:
                self.session.commit()
            
            # Update stats
            stats.increment("records_imported", result.imported_records)
            stats.increment("import_operations")
            
        except SQLAlchemyError as e:
            logger.error(f"Database error during import: {e}")
            self.session.rollback()
            result.add_error(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Error during import: {e}")
            self.session.rollback()
            result.add_error(f"Error: {str(e)}")
        
        result.finish()
        return result
    
    def import_file(self, file_path: Path, records: List[DataRecord], 
                   source_info: Optional[Dict[str, Any]] = None) -> ImportResult:
        """
        Import records from a file.
        
        Args:
            file_path: Path to the source file
            records: List of DataRecords to import
            source_info: Optional dictionary with source information
            
        Returns:
            ImportResult with import statistics
        """
        # Prepare source info
        if source_info is None:
            source_info = {}
        
        source_info['file_name'] = file_path.name
        
        # Import records
        return self.import_records(records, source_info)
    
    def close(self):
        """Close the database session."""
        self.session.close()
