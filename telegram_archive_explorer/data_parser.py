"""
Data parsing module for processing extracted text files.

This module handles the parsing of extracted files into structured data
that can be inserted into the database.
"""

import os
import logging
import re
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set, Iterator, NamedTuple
from dataclasses import dataclass
import itertools
from datetime import datetime
from urllib.parse import urlparse

from .logging_setup import stats

logger = logging.getLogger(__name__)

# Regular expressions for validation
URL_PATTERN = re.compile(r'^(https?://[^\s/$.?#].[^\s]*)')
EMAIL_PATTERN = re.compile(r'^([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)')
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.+-]{2,64}$')

# Error codes for validation
class ValidationError(Exception):
    """Raised when data validation fails."""
    pass

@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    error_message: Optional[str] = None

# Common delimiters to try when auto-detecting
COMMON_DELIMITERS = [':', ';', ',', '\t', '|', ' ']

class DataFormat:
    """Enumeration of recognized data formats."""
    URL_USER_PASS = "url_user_pass"  # URL:username:password
    USER_PASS_URL = "user_pass_url"  # username:password:URL
    USER_PASS = "user_pass"          # username:password
    EMAIL_PASS = "email_pass"        # email:password
    URL_ONLY = "url_only"            # Just URLs, one per line
    UNKNOWN = "unknown"              # Unrecognized format

@dataclass
class DataRecord:
    """Represents a structured data record from parsed text."""
    url: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    validation_errors: List[str] = None

    def __post_init__(self):
        """Validate and normalize fields after initialization."""
        self.validation_errors = []
        try:
            if self.url:
                self.url = self._normalize_url(self.url)
        except ValidationError as e:
            self.validation_errors.append(f"Invalid URL: {str(e)}")
            self.url = None

        try:
            if self.username:
                self.username = self._normalize_username(self.username)
        except ValidationError as e:
            self.validation_errors.append(f"Invalid username: {str(e)}")
            self.username = None

        try:
            if self.email:
                self.email = self._normalize_email(self.email)
        except ValidationError as e:
            self.validation_errors.append(f"Invalid email: {str(e)}")
            self.email = None

        try:
            if self.password:
                self.password = self._normalize_password(self.password)
        except ValidationError as e:
            self.validation_errors.append(f"Invalid password: {str(e)}")
            self.password = None
        
        # Extract domain from URL if present
        self.domain = None
        if self.url:
            try:
                parsed_url = urlparse(self.url)
                if parsed_url.netloc:
                    self.domain = parsed_url.netloc
            except Exception:
                pass
    
    def _normalize_url(self, url: str) -> str:
        """Normalize and validate a URL."""
        if not url:
            raise ValidationError("URL cannot be empty")
            
        url = url.strip().lower()
        
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
            
        # Validate URL format
        if not URL_PATTERN.match(url):
            raise ValidationError("Invalid URL format")
            
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                raise ValidationError("URL must have scheme and domain")
        except Exception as e:
            raise ValidationError(f"URL parsing failed: {str(e)}")
            
        return url
    
    def _normalize_email(self, email: str) -> str:
        """Normalize and validate an email address."""
        if not email:
            raise ValidationError("Email cannot be empty")
            
        email = email.strip().lower()
        
        # Validate email format
        if not EMAIL_PATTERN.match(email):
            raise ValidationError("Invalid email format")
            
        # Additional validation
        parts = email.split('@')
        if len(parts) != 2 or not all(parts):
            raise ValidationError("Email must have exactly one @ with non-empty parts")
            
        if len(email) > 254:  # RFC 5321
            raise ValidationError("Email too long")
            
        return email
    
    def _normalize_username(self, username: str) -> str:
        """Normalize and validate a username."""
        if not username:
            raise ValidationError("Username cannot be empty")
            
        username = username.strip().lower()
        
        # Validate username format
        if not USERNAME_PATTERN.match(username):
            raise ValidationError("Invalid username format")
            
        return username
    
    def _normalize_password(self, password: str) -> str:
        """Normalize and validate a password."""
        if not password:
            raise ValidationError("Password cannot be empty")
            
        password = password.strip()
        
        # Basic password validation
        if len(password) > 100:  # Reasonable maximum length
            raise ValidationError("Password too long")
            
        if not any(c.isalnum() for c in password):
            raise ValidationError("Password must contain at least one alphanumeric character")
            
        return password
    
    def is_valid(self) -> bool:
        """Check if the record has valid required data."""
        # At minimum, need either (URL and password) or (username/email and password)
        has_identifier = bool(self.url or self.username or self.email)
        has_password = bool(self.password)
        return has_identifier and has_password and not self.validation_errors

    def is_complete(self) -> bool:
        """Check if the record has all possible fields."""
        return bool(self.url and (self.username or self.email) and self.password)
    
    def quality_score(self) -> float:
        """
        Calculate a quality score for the record.
        Returns a float between 0.0 and 1.0.
        """
        if not self.is_valid():
            return 0.0
            
        score = 0.0
        total_fields = 0
        
        # URL quality (0.3)
        if self.url:
            total_fields += 1
            if self.url.startswith('https://'):  # Prefer HTTPS
                score += 0.3
            else:
                score += 0.2
                
        # Username/Email quality (0.3)
        if self.email:
            total_fields += 1
            score += 0.3
        elif self.username:
            total_fields += 1
            score += 0.2
            
        # Password quality (0.4)
        if self.password:
            total_fields += 1
            pwd_score = 0.0
            if len(self.password) >= 8:  # Length
                pwd_score += 0.1
            if any(c.isupper() for c in self.password):  # Uppercase
                pwd_score += 0.1
            if any(c.isdigit() for c in self.password):  # Digits
                pwd_score += 0.1
            if any(not c.isalnum() for c in self.password):  # Special chars
                pwd_score += 0.1
            score += pwd_score
            
        # Normalize by number of fields present
        return score / total_fields if total_fields > 0 else 0.0
    
    def __eq__(self, other) -> bool:
        """
        Compare two records for equality.
        
        Args:
            other: Another DataRecord
            
        Returns:
            True if the records are identical
        """
        if not isinstance(other, DataRecord):
            return False
            
        return (self.url == other.url and
                self.username == other.username and
                self.email == other.email and
                self.password == other.password)
    
    def __repr__(self) -> str:
        """
        String representation of the record.
        
        Returns:
            String representation
        """
        parts = []
        if self.url:
            parts.append(f"url='{self.url}'")
        if self.username:
            parts.append(f"username='{self.username}'")
        if self.email:
            parts.append(f"email='{self.email}'")
        if self.password:
            parts.append("password='***'")
            
        return f"DataRecord({', '.join(parts)})"

@dataclass
class FileParseResult:
    """Result of parsing a file."""
    records: List[DataRecord]
    metadata: Dict[str, Any]
    error: Optional[str] = None
    quality_score: float = 0.0
    needs_review: bool = False

class DataParser:
    """Parser for extracting structured data from text files."""
    
    def __init__(self):
        """Initialize the data parser."""
        self.skipped_rows = []
        self.flagged_files = set()
        self.stats = {
            "total_files": 0,
            "parsed_files": 0,
            "skipped_files": 0,
            "flagged_files": 0,
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": 0
        }
    
    def detect_format(self, lines: List[str]) -> Tuple[str, str]:
        """
        Detect the format of data in the lines and the delimiter.
        
        Args:
            lines: List of text lines
            
        Returns:
            Tuple of (format, delimiter)
        """
        if not lines:
            return DataFormat.UNKNOWN, None
        
        # Get a sample of lines for detection (up to 10)
        sample_lines = [line.strip() for line in lines[:10] if line.strip()]
        if not sample_lines:
            return DataFormat.UNKNOWN, None
        
        # Try to detect delimiter
        delimiter_counts = {}
        
        for line in sample_lines:
            for delimiter in COMMON_DELIMITERS:
                parts = line.split(delimiter)
                if len(parts) >= 2:
                    # Count this delimiter if it works
                    delimiter_counts[delimiter] = delimiter_counts.get(delimiter, 0) + 1
        
        # Find most common delimiter that works for most lines
        best_delimiter = None
        max_count = 0
        
        for delimiter, count in delimiter_counts.items():
            if count > max_count and count >= len(sample_lines) * 0.7:  # At least 70% of lines should have this delimiter
                max_count = count
                best_delimiter = delimiter
        
        if not best_delimiter:
            # Check if these are just URLs, one per line
            url_count = sum(1 for line in sample_lines if URL_PATTERN.match(line))
            if url_count >= len(sample_lines) * 0.7:
                return DataFormat.URL_ONLY, None
            
            return DataFormat.UNKNOWN, None
        
        # Analyze the format using the best delimiter
        format_counts = {}
        
        for line in sample_lines:
            parts = line.split(best_delimiter)
            
            if len(parts) < 2:
                continue
                
            # Check for URL:user:pass format
            if len(parts) >= 3 and URL_PATTERN.match(parts[0].strip()):
                format_counts[DataFormat.URL_USER_PASS] = format_counts.get(DataFormat.URL_USER_PASS, 0) + 1
            
            # Check for user:pass:URL format
            elif len(parts) >= 3 and URL_PATTERN.match(parts[2].strip()):
                format_counts[DataFormat.USER_PASS_URL] = format_counts.get(DataFormat.USER_PASS_URL, 0) + 1
            
            # Check for user:pass format
            elif len(parts) == 2:
                # Check if first part is an email
                if EMAIL_PATTERN.match(parts[0].strip()):
                    format_counts[DataFormat.EMAIL_PASS] = format_counts.get(DataFormat.EMAIL_PASS, 0) + 1
                else:
                    format_counts[DataFormat.USER_PASS] = format_counts.get(DataFormat.USER_PASS, 0) + 1
        
        # Find most common format
        best_format = DataFormat.UNKNOWN
        max_count = 0
        
        for format_type, count in format_counts.items():
            if count > max_count:
                max_count = count
                best_format = format_type
        
        return best_format, best_delimiter
    
    def parse_line(self, line: str, format_type: str, delimiter: str) -> Optional[DataRecord]:
        """
        Parse a single line based on the detected format.
        
        Args:
            line: Text line
            format_type: Detected format type
            delimiter: Detected delimiter
            
        Returns:
            DataRecord or None if line couldn't be parsed
        """
        if not line.strip():
            return None
            
        try:
            if format_type == DataFormat.URL_ONLY:
                # Just a URL
                match = URL_PATTERN.match(line.strip())
                if match:
                    return DataRecord(url=match.group(1))
                return None
                
            if not delimiter:
                return None
                
            parts = [part.strip() for part in line.split(delimiter)]
            
            if format_type == DataFormat.URL_USER_PASS and len(parts) >= 3:
                # URL:username:password
                url = parts[0]
                username = parts[1]
                password = parts[2]
                
                # Check if username is actually an email
                if EMAIL_PATTERN.match(username):
                    email = username
                    username = None
                else:
                    email = None
                    
                return DataRecord(url=url, username=username, email=email, password=password)
                
            elif format_type == DataFormat.USER_PASS_URL and len(parts) >= 3:
                # username:password:URL
                username = parts[0]
                password = parts[1]
                url = parts[2]
                
                # Check if username is actually an email
                if EMAIL_PATTERN.match(username):
                    email = username
                    username = None
                else:
                    email = None
                    
                return DataRecord(url=url, username=username, email=email, password=password)
                
            elif format_type == DataFormat.USER_PASS and len(parts) >= 2:
                # username:password
                username = parts[0]
                password = parts[1]
                
                # Check if username is actually an email
                if EMAIL_PATTERN.match(username):
                    email = username
                    username = None
                else:
                    email = None
                    
                return DataRecord(username=username, email=email, password=password)
                
            elif format_type == DataFormat.EMAIL_PASS and len(parts) >= 2:
                # email:password
                email = parts[0]
                password = parts[1]
                
                return DataRecord(email=email, password=password)
            
            # If we get here, format is unknown or line doesn't match expected format
            return None
            
        except Exception as e:
            logger.debug(f"Failed to parse line: {line}. Error: {e}")
            return None
    
    def parse_file(self, file_path: Path) -> FileParseResult:
        """
        Parse a file and extract structured data records.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            FileParseResult containing parsed records, metadata, and quality metrics
        """
        self.skipped_rows = []
        records = []
        total_quality = 0.0
        
        metadata = {
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "total_lines": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "skipped_rows": 0,
            "format_detected": None,
            "delimiter": None,
            "parsed_timestamp": datetime.utcnow().isoformat(),
            "quality_metrics": {
                "avg_record_quality": 0.0,
                "complete_records": 0,
                "partial_records": 0,
                "error_rate": 0.0
            }
        }
        
        if not file_path.exists():
            return FileParseResult(
                records=[],
                metadata=metadata,
                error="File does not exist",
                needs_review=True
            )
            
        try:
            # Read all lines from the file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            metadata["total_lines"] = len(lines)
            
            # Skip empty files
            if not lines:
                return FileParseResult(
                    records=[],
                    metadata=metadata,
                    error="File is empty",
                    needs_review=True
                )
                
            # Detect format and delimiter
            format_type, delimiter = self.detect_format(lines)
            metadata["format_detected"] = format_type
            metadata["delimiter"] = delimiter
            
            if format_type == DataFormat.UNKNOWN:
                # Try to handle other file types or CSV files
                try:
                    # Check if it's a CSV file
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        # Try to sniff the CSV dialect
                        sample = f.read(1024)
                        f.seek(0)
                        
                        try:
                            dialect = csv.Sniffer().sniff(sample)
                            reader = csv.reader(f, dialect)
                            
                            # Read and process CSV rows
                            for row in reader:
                                metadata["total_lines"] += 1
                                
                                if len(row) >= 2:
                                    # Try to identify columns
                                    if len(row) >= 3:
                                        # Try to find URL, username, and password columns
                                        url_idx = username_idx = password_idx = None
                                        
                                        for i, value in enumerate(row):
                                            if URL_PATTERN.match(value.strip()):
                                                url_idx = i
                                            elif EMAIL_PATTERN.match(value.strip()):
                                                username_idx = i
                                            elif not url_idx and not username_idx and i == 0:
                                                username_idx = i
                                            elif not password_idx and i > 0:
                                                password_idx = i
                                        
                                        if (url_idx is not None or username_idx is not None) and password_idx is not None:
                                            record = DataRecord(
                                                url=row[url_idx] if url_idx is not None else None,
                                                username=row[username_idx] if username_idx is not None and not EMAIL_PATTERN.match(row[username_idx].strip()) else None,
                                                email=row[username_idx] if username_idx is not None and EMAIL_PATTERN.match(row[username_idx].strip()) else None,
                                                password=row[password_idx]
                                            )
                                            
                                            if record.is_valid():
                                                records.append(record)
                                                metadata["valid_records"] += 1
                                            else:
                                                metadata["invalid_records"] += 1
                                                self.skipped_rows.append(row)
                                        else:
                                            metadata["invalid_records"] += 1
                                            self.skipped_rows.append(row)
                                    else:
                                        # Try username:password format
                                        record = DataRecord(
                                            username=None if EMAIL_PATTERN.match(row[0].strip()) else row[0],
                                            email=row[0] if EMAIL_PATTERN.match(row[0].strip()) else None,
                                            password=row[1]
                                        )
                                        
                                        if record.is_valid():
                                            records.append(record)
                                            metadata["valid_records"] += 1
                                        else:
                                            metadata["invalid_records"] += 1
                                            self.skipped_rows.append(row)
                                else:
                                    metadata["invalid_records"] += 1
                                    self.skipped_rows.append(row)
                                    
                            # Update metadata
                            metadata["format_detected"] = "CSV"
                            metadata["delimiter"] = dialect.delimiter
                            metadata["skipped_rows"] = len(self.skipped_rows)
                            
                            # Flag file if too many rows were skipped
                            if metadata["invalid_records"] > metadata["valid_records"] * 0.3:  # More than 30% invalid
                                metadata["flagged"] = True
                                self.flagged_files.add(str(file_path))
                                
                            return records, metadata
                            
                        except Exception:
                            # Not a CSV file, continue with line-by-line processing
                            pass
                except Exception as e:
                    logger.error(f"Failed to parse CSV file {file_path}: {e}")
            
            # Process line by line
            for line_num, line in enumerate(lines, 1):
                record = self.parse_line(line, format_type, delimiter)
                
                if record and record.is_valid():
                    records.append(record)
                    metadata["valid_records"] += 1
                else:
                    metadata["invalid_records"] += 1
                    self.skipped_rows.append(line)
            
            metadata["skipped_rows"] = len(self.skipped_rows)
            
            # Flag file if too many rows were skipped
            if metadata["invalid_records"] > metadata["valid_records"] * 0.3:  # More than 30% invalid
                metadata["flagged"] = True
                self.flagged_files.add(str(file_path))
            
            # Update global stats
            self.stats["total_files"] += 1
            self.stats["parsed_files"] += 1
            self.stats["total_records"] += metadata["total_lines"]
            self.stats["valid_records"] += metadata["valid_records"]
            self.stats["invalid_records"] += metadata["invalid_records"]
            
            # Calculate quality metrics
            metadata["quality_metrics"]["avg_record_quality"] = total_quality / len(records) if records else 0.0
            metadata["quality_metrics"]["complete_records"] = sum(1 for r in records if r.is_complete())
            metadata["quality_metrics"]["partial_records"] = len(records) - metadata["quality_metrics"]["complete_records"]
            metadata["quality_metrics"]["error_rate"] = metadata["invalid_records"] / metadata["total_lines"] if metadata["total_lines"] > 0 else 0.0
            
            # Track statistics
            stats.increment("files_parsed")
            stats.increment("records_parsed", metadata["valid_records"])
            
            # Determine if file needs review
            needs_review = (
                metadata["quality_metrics"]["error_rate"] > 0.3 or  # More than 30% errors
                metadata["quality_metrics"]["avg_record_quality"] < 0.5 or  # Low average quality
                len(records) == 0  # No valid records found
            )
            
            if needs_review:
                self.flagged_files.add(str(file_path))
                self.stats["flagged_files"] += 1
            
            return FileParseResult(
                records=records,
                metadata=metadata,
                quality_score=metadata["quality_metrics"]["avg_record_quality"],
                needs_review=needs_review
            )
            
        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {e}", exc_info=True)
            self.stats["skipped_files"] += 1
            return FileParseResult(
                records=[],
                metadata=metadata,
                error=str(e),
                needs_review=True
            )
    
    def parse_directory(self, directory_path: Path) -> Iterator[Tuple[List[DataRecord], Dict[str, Any]]]:
        """
        Parse all text files in a directory.
        
        Args:
            directory_path: Path to directory
            
        Yields:
            Tuples of (list of DataRecords, metadata dictionary) for each file
        """
        if not directory_path.exists() or not directory_path.is_dir():
            logger.error(f"Directory does not exist: {directory_path}")
            return
            
        # Get all text files
        text_files = [
            p for p in directory_path.glob("**/*") 
            if p.is_file() and p.suffix.lower() in ['.txt', '.csv', '.log', '.tsv', '.dat']
        ]
        
        for file_path in text_files:
            yield self.parse_file(file_path)
    
    def get_skipped_rows(self) -> List[str]:
        """
        Get the list of skipped rows from the last parse operation.
        
        Returns:
            List of skipped rows
        """
        return self.skipped_rows
    
    def get_flagged_files(self) -> Set[str]:
        """
        Get the set of flagged file paths.
        
        Returns:
            Set of flagged file paths
        """
        return self.flagged_files
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get parsing statistics.
        
        Returns:
            Dictionary with parsing statistics
        """
        return self.stats
