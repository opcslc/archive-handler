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

from .database import db, URL, Credential, Source, ImportLog
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
        self.skipped_details = []  # List of skipped record details
        self.error_details = []    # List of error details
        self.import_metadata = {}  # Additional metadata about the import
        self.last_progress = 0     # Last reported progress percentage
    
    def add_error(self, error_message: str, record: Optional[DataRecord] = None):
        """
        Add an error message with optional record details.
        
        Args:
            error_message: Error message to add
            record: Optional DataRecord that caused the error
        """
        self.errors.append(error_message)
        self.error_records += 1
        if record:
            detail = {
                'message': error_message,
                'source_file': record.source_file,
                'line_number': record.line_number,
                'timestamp': datetime.utcnow().isoformat()
            }
            self.error_details.append(detail)
            logger.error(f"Import error: {error_message} in file {record.source_file} at line {record.line_number}")

    def add_skipped(self, reason: str, record: DataRecord):
        """
        Log a skipped record with details.
        
        Args:
            reason: Reason for skipping
            record: DataRecord that was skipped
        """
        self.skipped_records += 1
        detail = {
            'reason': reason,
            'source_file': record.source_file,
            'line_number': record.line_number,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.skipped_details.append(detail)
        logger.warning(f"Skipped record: {reason} in file {record.source_file} at line {record.line_number}")

    def update_progress(self, processed_records: int):
        """
        Update and log import progress if significant change.
        
        Args:
            processed_records: Number of records processed so far
        """
        progress = min(100, int((processed_records / self.total_records) * 100))
        if progress - self.last_progress >= 5:  # Log every 5% progress
            self.last_progress = progress
            duration = time.time() - self.start_time
            rate = processed_records / duration if duration > 0 else 0
            logger.info(f"Import progress: {progress}% ({processed_records}/{self.total_records}) - {rate:.1f} records/sec")
    
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
    
    def __init__(self, session: Optional[Session] = None, batch_size: int = 1000):
        """
        Initialize the data importer.
        
        Args:
            session: Optional database session. If None, creates a new session.
            batch_size: Number of records to process in each batch (default: 1000)
        """
        self.session = session or db.get_session()
        self.batch_size = batch_size
        self.url_cache: Dict[str, URL] = {}     # Cache to reduce duplicate URL queries
        self.credential_cache: Dict[str, Credential] = {}  # Cache to reduce duplicate credential queries
        self.current_import_log: Optional[ImportLog] = None  # Track current import operation
    
    def _find_existing_url(self, url: str) -> Optional[URL]:
        """
        Find an existing URL in the database.
        
        Args:
            url: URL to find
            
        Returns:
            URL entity or None if not found
        """
        # Check cache first
        cached = self.url_cache.get(url)
        if cached is not None:
            return cached
            
        # Query database
        existing = self.session.query(URL).filter(URL.url == url).first()
        
        # Update cache
        self.url_cache[url] = existing
        
        return existing
    
    def _find_existing_credential(self, username: Optional[str], 
                               email: Optional[str], 
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
        # Generate cache key
        cache_key = f"{username}:{email}:{password}"
        cached = self.credential_cache.get(cache_key)
        if cached is not None:
            return cached
            
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
        Import a single data record with enhanced duplicate detection and metadata.
        
        Args:
            record: DataRecord to import
            source: Source entity for this record
            
        Returns:
            Tuple of (success, message)
        """
        try:
            duplicate_found = False
            duplicate_details = []
            
            # URL handling with enhanced duplicate detection
            url_entity = None
            if record.url:
                url_entity = self._find_existing_url(record.url)
                if url_entity:
                    duplicate_found = True
                    duplicate_details.append(f"URL: {record.url}")
                else:
                    # Create new URL with metadata
                    url_entity = URL(
                        url=record.url,
                        source=source,
                        first_seen=datetime.utcnow(),
                        metadata={
                            'source_file': record.source_file,
                            'line_number': record.line_number,
                            'validation_score': getattr(record, 'quality_score', None)
                        }
                    )
                    self.session.add(url_entity)
                    self.url_cache[record.url] = url_entity
            
            # Enhanced credential handling with duplicate detection
            credential_entity = None
            if record.password and (record.username or record.email):
                credential_entity = self._find_existing_credential(
                    record.username, record.email, record.password
                )
                
                if credential_entity:
                    duplicate_found = True
                    duplicate_details.append(
                        f"Credential: {record.username or record.email}"
                    )
                else:
                    # Create new credential with metadata
                    credential_entity = Credential(
                        username=record.username,
                        email=record.email,
                        password=record.password,
                        source=source,
                        first_seen=datetime.utcnow(),
                        metadata={
                            'source_file': record.source_file,
                            'line_number': record.line_number,
                            'validation_score': getattr(record, 'quality_score', None)
                        }
                    )
                    self.session.add(credential_entity)
                    cache_key = f"{record.username}:{record.email}:{record.password}"
                    self.credential_cache[cache_key] = credential_entity
            
            # Handle relationships and duplicates
            if url_entity and credential_entity:
                if url_entity not in credential_entity.urls:
                    credential_entity.urls.append(url_entity)
                    if duplicate_found:
                        # Log relationship between existing entities
                        logger.info(f"Added relationship between existing entities: "
                                  f"URL({url_entity.url}) - "
                                  f"Credential({credential_entity.username or credential_entity.email})")
            
            if duplicate_found:
                return False, f"Duplicate record found: {', '.join(duplicate_details)}"
            
            return True, "Record imported successfully"
            
        except Exception as e:
            logger.error(f"Error importing record: {e}")
            return False, f"Error: {str(e)}"
    
    def _create_import_log(self, source: Source, total_records: int) -> ImportLog:
        """Create a new import log entry."""
        import uuid
        
        import_log = ImportLog(
            batch_id=str(uuid.uuid4()),
            start_time=datetime.utcnow(),
            total_records=total_records,
            source=source,
            metadata={
                'batch_size': self.batch_size,
                'started_at': datetime.utcnow().isoformat()
            }
        )
        self.session.add(import_log)
        self.session.flush()  # Get the ID without committing
        return import_log

    def _commit_batch(self, batch: List[DataRecord], result: ImportResult) -> None:
        """
        Commit a batch of records with error handling.
        
        Args:
            batch: List of records in current batch
            result: ImportResult to update with any errors
        """
        try:
            self.session.flush()  # Test the batch
            self.session.commit()  # Commit if successful
        except SQLAlchemyError as e:
            # Roll back only this batch
            self.session.rollback()
            error_msg = f"Batch commit failed: {str(e)}"
            for record in batch:
                result.add_error(error_msg, record)
                if self.current_import_log is not None:
                    self.current_import_log.error_records += 1
            logger.error(f"Failed to commit batch: {str(e)}")

    def import_records(self, records: List[DataRecord], 
                      source_info: Dict[str, Any]) -> ImportResult:
        """
        Import a list of data records with transaction support and detailed tracking.
        
        Args:
            records: List of DataRecords to import
            source_info: Dictionary with source information including:
                - channel: Telegram channel name
                - message_id: Optional message ID
                - file_name: Original file name
                - collected_date: Date data was collected
                
        Returns:
            ImportResult with detailed import statistics and tracking
        """
        result = ImportResult()
        result.total_records = len(records)
        result.import_metadata.update({
            'started_at': datetime.utcnow().isoformat(),
            'source_info': source_info,
            'batch_size': self.batch_size
        })
        
        # Begin transaction and create import log
        try:
            source = self._create_or_update_source(source_info)
            self.current_import_log = self._create_import_log(source, len(records))
            self.session.flush()  # Ensure source and log are created
            
            # Process records in batches with tracking
            batch_count = 0
            processed_count = 0
            current_batch = []
            
            for record in records:
                processed_count += 1
                
                # Validate record
                if not record.is_valid():
                    result.add_skipped("Invalid record format", record)
                    continue
                
                try:
                    # Try to import the record
                    success, message = self.import_record(record, source)
                    
                    if success:
                        result.imported_records += 1
                        if self.current_import_log is not None:
                            self.current_import_log.imported_records += 1
                        current_batch.append(record)
                    else:
                        if "Duplicate" in message:
                            result.duplicate_records += 1
                            if self.current_import_log is not None:
                                self.current_import_log.duplicate_records += 1
                        else:
                            result.add_error(message, record)
                            if self.current_import_log is not None:
                                self.current_import_log.error_records += 1
                    
                    # Handle batch commits with savepoints
                    batch_count += 1
                    if batch_count >= self.batch_size:
                        try:
                            self.session.flush()  # Test the batch
                            self.session.commit()  # Commit if successful
                            batch_count = 0
                            current_batch = []
                        except SQLAlchemyError as e:
                            # Roll back only this batch
                            self.session.rollback()
                            for failed_record in current_batch:
                                result.add_error(f"Batch commit failed: {str(e)}", failed_record)
                            current_batch = []
                            batch_count = 0
                    
                    # Update progress tracking
                    result.update_progress(processed_count)
                    
                except Exception as e:
                    # Handle individual record errors without failing the entire import
                    result.add_error(f"Record processing error: {str(e)}", record)
                    logger.exception(f"Error processing record from {record.source_file}")
            
            # Final commit for any remaining records
            if current_batch:
                try:
                    self.session.flush()
                    self.session.commit()
                except SQLAlchemyError as e:
                    self.session.rollback()
                    for failed_record in current_batch:
                        result.add_error(f"Final batch commit failed: {str(e)}", failed_record)
            
            # Update import statistics
            stats.increment("records_imported", result.imported_records)
            stats.increment("records_skipped", result.skipped_records)
            stats.increment("records_failed", result.error_records)
            stats.increment("import_operations")
            
            result.import_metadata['completed_at'] = datetime.utcnow().isoformat()
            
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
