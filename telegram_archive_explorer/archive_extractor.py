"""
Archive extraction functionality for downloaded files.

This module handles the extraction of various archive formats and manages
password-protected archives.
"""

import os
import logging
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import zipfile
import tarfile
import re
from datetime import datetime

from .logging_setup import stats

logger = logging.getLogger(__name__)

# List of supported archive extensions
SUPPORTED_EXTENSIONS = {
    '.zip': 'zip',
    '.rar': 'rar',
    '.7z': '7z',
    '.tar': 'tar',
    '.gz': 'gzip',
    '.bz2': 'bzip2',
    '.xz': 'xz',
    '.tar.gz': 'tar_gzip',
    '.tgz': 'tar_gzip',
    '.tar.bz2': 'tar_bzip2',
    '.tbz2': 'tar_bzip2',
    '.tar.xz': 'tar_xz',
    '.txz': 'tar_xz'
}

class PasswordRequiredError(Exception):
    """Exception raised when an archive requires a password."""
    pass

class UnsupportedArchiveError(Exception):
    """Exception raised when an archive format is not supported."""
    pass

class ArchiveExtractor:
    """Handles extraction of various archive formats."""
    
    def __init__(self, temp_dir: Optional[Path] = None):
        """
        Initialize the archive extractor.
        
        Args:
            temp_dir: Optional directory for temporary extraction.
                     If None, uses the system temp directory.
        """
        if temp_dir:
            self.temp_dir = temp_dir
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.temp_dir = Path(tempfile.gettempdir()) / "telegram_archive_explorer"
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Dictionary to store queued password-protected archives
        # Key: archive path, Value: Dict with metadata
        self.password_queue = {}
        
        # Set of additional dependencies that need to be installed
        self._missing_dependencies = set()
    
    def detect_archive_type(self, file_path: Path) -> str:
        """
        Detect the type of archive from its filename.
        
        Args:
            file_path: Path to the archive file
            
        Returns:
            String identifying the archive type
            
        Raises:
            UnsupportedArchiveError: If the archive type is not supported
        """
        file_name = file_path.name.lower()
        
        # Check for compound extensions first (e.g., .tar.gz)
        for ext in ['.tar.gz', '.tar.bz2', '.tar.xz']:
            if file_name.endswith(ext):
                return SUPPORTED_EXTENSIONS[ext]
        
        # Check for simple extensions
        for ext, archive_type in SUPPORTED_EXTENSIONS.items():
            if file_name.endswith(ext):
                return archive_type
        
        raise UnsupportedArchiveError(f"Unsupported archive format: {file_path}")
    
    def _check_dependencies(self, archive_type: str) -> bool:
        """
        Check if all required dependencies for a specific archive type are installed.
        
        Args:
            archive_type: Type of archive
            
        Returns:
            True if all dependencies are available, False otherwise
        """
        try:
            if archive_type == 'rar':
                import rarfile
                return True
            elif archive_type == '7z':
                import py7zr
                return True
            elif archive_type in ['zip', 'tar', 'gzip', 'bzip2', 'xz', 
                                'tar_gzip', 'tar_bzip2', 'tar_xz']:
                # These are supported by the standard library
                return True
            else:
                return False
        except ImportError:
            if archive_type == 'rar':
                self._missing_dependencies.add('rarfile')
            elif archive_type == '7z':
                self._missing_dependencies.add('py7zr')
            
            return False
    
    def extract_zip(self, file_path: Path, extract_to: Path, password: Optional[str] = None) -> List[Path]:
        """
        Extract a ZIP archive.
        
        Args:
            file_path: Path to the ZIP file
            extract_to: Directory to extract to
            password: Optional password for encrypted archives
            
        Returns:
            List of paths to extracted files
            
        Raises:
            PasswordRequiredError: If the archive is password-protected and no password is provided
            Exception: For other extraction errors
        """
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # Check if password protected
                for zip_info in zip_ref.infolist():
                    if zip_info.flag_bits & 0x1:
                        if not password:
                            raise PasswordRequiredError("ZIP file is password protected")
                        break
                
                # Extract files
                pwd = password.encode('utf-8') if password else None
                zip_ref.extractall(path=extract_to, pwd=pwd)
                
                # Return list of extracted files
                return [extract_to / name for name in zip_ref.namelist()]
                
        except zipfile.BadZipFile:
            logger.error(f"Invalid or corrupted ZIP file: {file_path}")
            raise
        except RuntimeError as e:
            if "password required" in str(e).lower() or "bad password" in str(e).lower():
                raise PasswordRequiredError("ZIP file is password protected")
            raise
    
    def extract_tar(self, file_path: Path, extract_to: Path) -> List[Path]:
        """
        Extract a TAR archive (including compressed variants).
        
        Args:
            file_path: Path to the TAR file
            extract_to: Directory to extract to
            
        Returns:
            List of paths to extracted files
        """
        try:
            with tarfile.open(file_path) as tar_ref:
                # Get list of files before extraction
                members = tar_ref.getmembers()
                
                # Check for potentially unsafe paths (directory traversal attacks)
                for member in members:
                    member_path = Path(member.name)
                    if member_path.is_absolute() or '..' in member_path.parts:
                        logger.warning(f"Potentially unsafe path in archive: {member.name}")
                        # Make the path safe by removing leading slashes and parent directory references
                        member.name = str(Path(*[part for part in member_path.parts if part != '..']))
                
                # Extract files
                tar_ref.extractall(path=extract_to)
                
                # Return list of extracted files
                return [extract_to / member.name for member in members]
        except Exception as e:
            logger.error(f"Failed to extract TAR file {file_path}: {e}")
            raise
    
    def extract_rar(self, file_path: Path, extract_to: Path, password: Optional[str] = None) -> List[Path]:
        """
        Extract a RAR archive.
        
        Args:
            file_path: Path to the RAR file
            extract_to: Directory to extract to
            password: Optional password for encrypted archives
            
        Returns:
            List of paths to extracted files
            
        Raises:
            PasswordRequiredError: If the archive is password-protected and no password is provided
            Exception: For other extraction errors
        """
        try:
            import rarfile
        except ImportError:
            self._missing_dependencies.add('rarfile')
            logger.error("rarfile module not installed. Install it with 'pip install rarfile'")
            raise
        
        try:
            with rarfile.RarFile(file_path) as rar_ref:
                # Check if password protected
                if rar_ref.needs_password():
                    if not password:
                        raise PasswordRequiredError("RAR file is password protected")
                    rar_ref.setpassword(password)
                
                # Extract files
                rar_ref.extractall(path=extract_to)
                
                # Return list of extracted files
                return [extract_to / name for name in rar_ref.namelist()]
                
        except rarfile.BadRarFile:
            logger.error(f"Invalid or corrupted RAR file: {file_path}")
            raise
        except rarfile.PasswordRequiredError:
            raise PasswordRequiredError("RAR file is password protected")
        except rarfile.BadRarPassword:
            raise PasswordRequiredError("Incorrect password for RAR file")
    
    def extract_7z(self, file_path: Path, extract_to: Path, password: Optional[str] = None) -> List[Path]:
        """
        Extract a 7Z archive.
        
        Args:
            file_path: Path to the 7Z file
            extract_to: Directory to extract to
            password: Optional password for encrypted archives
            
        Returns:
            List of paths to extracted files
            
        Raises:
            PasswordRequiredError: If the archive is password-protected and no password is provided
            Exception: For other extraction errors
        """
        try:
            import py7zr
        except ImportError:
            self._missing_dependencies.add('py7zr')
            logger.error("py7zr module not installed. Install it with 'pip install py7zr'")
            raise
        
        try:
            with py7zr.SevenZipFile(file_path, mode='r', password=password) as z:
                z.extractall(path=extract_to)
                
                # Get list of extracted files
                extracted_files = []
                for name in z.getnames():
                    extracted_files.append(extract_to / name)
                
                return extracted_files
                
        except py7zr.Bad7zFile:
            logger.error(f"Invalid or corrupted 7Z file: {file_path}")
            raise
        except Exception as e:
            if "password is required" in str(e).lower() or "password required" in str(e).lower():
                raise PasswordRequiredError("7Z file is password protected")
            raise
    
    def extract(self, file_path: Path, extract_to: Optional[Path] = None, 
                password: Optional[str] = None, 
                message_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract an archive file.
        
        Args:
            file_path: Path to the archive file
            extract_to: Directory to extract to (if None, creates a temp directory)
            password: Optional password for encrypted archives
            message_info: Optional metadata about the Telegram message
            
        Returns:
            Dictionary with extraction information:
                {
                    'success': bool,
                    'extracted_path': Path or None,
                    'extracted_files': List[Path] or [],
                    'error': str or None,
                    'password_required': bool,
                    'archive_type': str
                }
        """
        # Create a unique extraction directory if not provided
        if extract_to is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extract_to = self.temp_dir / f"extract_{Path(file_path).stem}_{timestamp}"
        
        # Create extraction directory
        extract_to.mkdir(parents=True, exist_ok=True)
        
        result = {
            'success': False,
            'extracted_path': extract_to,
            'extracted_files': [],
            'error': None,
            'password_required': False,
            'archive_type': None
        }
        
        try:
            # Detect archive type
            archive_type = self.detect_archive_type(file_path)
            result['archive_type'] = archive_type
            
            # Check dependencies for this archive type
            if not self._check_dependencies(archive_type):
                missing = ', '.join(self._missing_dependencies)
                error_message = f"Missing dependencies for {archive_type} extraction: {missing}"
                logger.error(error_message)
                result['error'] = error_message
                return result
            
            # Extract based on archive type
            if archive_type == 'zip':
                result['extracted_files'] = self.extract_zip(file_path, extract_to, password)
            elif archive_type in ['tar', 'tar_gzip', 'tar_bzip2', 'tar_xz', 'tgz', 'tbz2', 'txz']:
                result['extracted_files'] = self.extract_tar(file_path, extract_to)
            elif archive_type == 'rar':
                result['extracted_files'] = self.extract_rar(file_path, extract_to, password)
            elif archive_type == '7z':
                result['extracted_files'] = self.extract_7z(file_path, extract_to, password)
            else:
                raise UnsupportedArchiveError(f"Extraction not implemented for {archive_type}")
                
            result['success'] = True
            stats.increment("archives_extracted")
            
        except PasswordRequiredError as e:
            logger.info(f"Password required for archive: {file_path}")
            result['error'] = str(e)
            result['password_required'] = True
            
            # Queue this archive for later processing
            if file_path not in self.password_queue:
                self.password_queue[file_path] = {
                    'path': file_path,
                    'extract_to': extract_to,
                    'message_info': message_info,
                    'attempts': 0,
                    'queued_at': datetime.now()
                }
                
        except UnsupportedArchiveError as e:
            logger.error(f"Unsupported archive format: {file_path}")
            result['error'] = str(e)
            
        except Exception as e:
            logger.error(f"Failed to extract archive {file_path}: {e}", exc_info=True)
            result['error'] = str(e)
        
        return result
    
    def extract_with_password(self, file_path: Path, password: str, extract_to: Optional[Path] = None) -> Dict[str, Any]:
        """
        Extract a password-protected archive.
        
        Args:
            file_path: Path to the archive file
            password: Password for the archive
            extract_to: Directory to extract to (if None, creates a temp directory)
            
        Returns:
            Result dictionary (same as extract method)
        """
        # Get queued archive info if it exists
        queue_info = self.password_queue.get(file_path)
        
        if queue_info:
            # Use the original extraction path
            extract_to = queue_info.get('extract_to') or extract_to
            message_info = queue_info.get('message_info')
            
            # Increment attempt counter
            queue_info['attempts'] += 1
            
            # Try extraction with password
            result = self.extract(file_path, extract_to, password, message_info)
            
            # Remove from queue if successful
            if result['success']:
                del self.password_queue[file_path]
            
            return result
        else:
            # Direct extraction request
            return self.extract(file_path, extract_to, password)
    
    def get_password_queue(self) -> List[Dict[str, Any]]:
        """
        Get the list of archives waiting for passwords.
        
        Returns:
            List of dictionaries with information about queued archives
        """
        return [
            {
                'path': str(info['path']),
                'queued_at': info['queued_at'],
                'attempts': info['attempts'],
                'message_info': info['message_info']
            }
            for path, info in self.password_queue.items()
        ]
    
    def cleanup(self, extract_path: Optional[Path] = None):
        """
        Clean up extracted files.
        
        Args:
            extract_path: Specific extraction path to clean.
                         If None, cleans all temporary directories.
        """
        if extract_path and extract_path.exists():
            # Clean specific extraction path
            try:
                if extract_path.is_dir():
                    shutil.rmtree(extract_path)
                else:
                    extract_path.unlink()
                logger.info(f"Cleaned up {extract_path}")
            except Exception as e:
                logger.error(f"Failed to clean up {extract_path}: {e}")
        elif not extract_path:
            # Clean all temporary directories that are not in the password queue
            protected_paths = {info['extract_to'] for info in self.password_queue.values()}
            
            try:
                for path in self.temp_dir.iterdir():
                    if path.is_dir() and path not in protected_paths:
                        try:
                            shutil.rmtree(path)
                            logger.info(f"Cleaned up temporary directory {path}")
                        except Exception as e:
                            logger.error(f"Failed to clean up {path}: {e}")
            except Exception as e:
                logger.error(f"Failed to clean up temporary directories: {e}")
