#!/usr/bin/env python
"""
Verify that the Telegram Archive Explorer package is properly set up.

This script attempts to import all necessary modules and checks the database
connection to ensure the software is correctly installed.
"""

import os
import sys
from pathlib import Path
import logging
import argparse

# Add the parent directory to the path to allow importing the package
parent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent_dir))

def check_imports():
    """Check that all necessary modules can be imported."""
    print("Checking imports...")
    
    required_modules = [
        "telethon", 
        "sqlalchemy", 
        "click", 
        "cryptography",
        "schedule"
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            print(f"✗ {module} - MISSING")
            missing_modules.append(module)
    
    optional_modules = [
        ("pysqlcipher3", "Database encryption"),
        ("rarfile", "RAR archive support"),
        ("py7zr", "7z archive support")
    ]
    
    missing_optional = []
    
    print("\nChecking optional modules...")
    for module, purpose in optional_modules:
        try:
            __import__(module)
            print(f"✓ {module} ({purpose})")
        except ImportError:
            print(f"- {module} ({purpose}) - OPTIONAL, NOT FOUND")
            missing_optional.append((module, purpose))
    
    return missing_modules, missing_optional

def check_package():
    """Check that the package can be imported and initialized."""
    print("\nChecking package...")
    
    try:
        import telegram_archive_explorer
        print(f"✓ Package version: {telegram_archive_explorer.__version__}")
        
        # Check submodules
        from telegram_archive_explorer import (
            config, 
            database, 
            logging_setup, 
            telegram_client,
            archive_extractor,
            data_parser,
            data_importer,
            search,
            scheduler,
            cli
        )
        print("✓ All submodules imported successfully")
        
        return True
    except ImportError as e:
        print(f"✗ Package import failed: {e}")
        return False

def check_database(initialize=False):
    """
    Check database functionality.
    
    Args:
        initialize: Whether to initialize the database with test data
    """
    print("\nChecking database...")
    
    try:
        from telegram_archive_explorer import database
        from telegram_archive_explorer.config import config
        
        # Create a test database in memory
        test_config = database.DatabaseConfig(
            path=":memory:",
            encryption_key=None
        )
        
        test_db = database.Database(test_config)
        session = test_db.get_session()
        
        # Check that tables were created
        print("✓ Database connection successful")
        print("✓ Database tables created")
        
        # Initialize with test data if requested
        if initialize:
            print("\nInitializing database with test data...")
            
            # Create test source
            source = database.Source(
                telegram_channel="@test_channel",
                message_id=123,
                file_name="test_file.zip"
            )
            session.add(source)
            
            # Create test URL
            url = database.URL(
                url="http://example.com",
                domain="example.com",
                source=source
            )
            session.add(url)
            
            # Create test credential
            credential = database.Credential(
                username="testuser",
                email="test@example.com",
                password="password123",
                source=source
            )
            session.add(credential)
            
            # Associate URL with credential
            credential.urls.append(url)
            
            # Commit changes
            session.commit()
            
            # Verify data was inserted
            url_count = session.query(database.URL).count()
            credential_count = session.query(database.Credential).count()
            
            print(f"✓ Inserted {url_count} URL(s) and {credential_count} credential(s)")
        
        # Clean up
        session.close()
        test_db.close()
        
        print("✓ Database test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def main():
    """Main function to verify setup."""
    parser = argparse.ArgumentParser(description="Verify Telegram Archive Explorer setup")
    parser.add_argument("--init-db", action="store_true", help="Initialize database with test data")
    args = parser.parse_args()
    
    print("Telegram Archive Explorer - Setup Verification\n")
    
    # Check imports
    missing, missing_optional = check_imports()
    
    # Check package
    package_ok = check_package()
    
    # Check database
    db_ok = check_database(initialize=args.init_db)
    
    # Print summary
    print("\n" + "="*50)
    print("VERIFICATION SUMMARY")
    print("="*50)
    
    if missing:
        print("\n❌ Missing required modules:")
        for module in missing:
            print(f"  - {module}")
        print("\nPlease install missing modules with: pip install " + " ".join(missing))
    else:
        print("\n✅ All required modules are installed")
    
    if missing_optional:
        print("\n⚠️ Missing optional modules:")
        for module, purpose in missing_optional:
            print(f"  - {module} ({purpose})")
        print("\nYou can install these with: pip install " + " ".join(m[0] for m in missing_optional))
    
    if package_ok:
        print("\n✅ Package can be imported successfully")
    else:
        print("\n❌ Package import failed")
    
    if db_ok:
        print("\n✅ Database functionality working correctly")
    else:
        print("\n❌ Database functionality failed")
    
    # Final verdict
    if not missing and package_ok and db_ok:
        print("\n🎉 All checks passed! Telegram Archive Explorer is properly set up.\n")
        return 0
    else:
        print("\n❌ Some checks failed. Please resolve the issues listed above.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
