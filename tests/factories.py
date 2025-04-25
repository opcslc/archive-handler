import random
import string
from datetime import datetime, timedelta
from telegram_archive_explorer.database import DataRecord

class TestDataFactory:
    """Factory class for generating test data"""
    
    @staticmethod
    def random_string(length=10):
        """Generate a random string"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_email():
        """Generate a random email address"""
        username = TestDataFactory.random_string(8)
        domain = TestDataFactory.random_string(6)
        tld = random.choice(['com', 'org', 'net', 'edu'])
        return f"{username}@{domain}.{tld}"
    
    @staticmethod
    def random_url():
        """Generate a random URL"""
        domain = TestDataFactory.random_string(8)
        tld = random.choice(['com', 'org', 'net', 'edu'])
        protocol = random.choice(['http', 'https'])
        return f"{protocol}://{domain}.{tld}"
    
    @staticmethod
    def random_password():
        """Generate a random password"""
        chars = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choices(chars, k=random.randint(8, 16)))

    @staticmethod
    def create_data_record(**kwargs):
        """Create a DataRecord with random or specified data"""
        data = {
            'url': kwargs.get('url', TestDataFactory.random_url()),
            'username': kwargs.get('username', TestDataFactory.random_email()),
            'password': kwargs.get('password', TestDataFactory.random_password()),
            'source_info': kwargs.get('source_info', {
                'channel_id': random.randint(1000, 9999),
                'message_id': random.randint(1, 1000),
                'file': f"archive_{TestDataFactory.random_string()}.zip"
            }),
            'created_at': kwargs.get('created_at', datetime.utcnow()),
            'updated_at': kwargs.get('updated_at', datetime.utcnow())
        }
        return DataRecord(**data)

    @staticmethod
    def create_batch(count, **kwargs):
        """Create multiple DataRecords"""
        return [TestDataFactory.create_data_record(**kwargs) for _ in range(count)]

    @staticmethod
    def create_related_records(base_count=5, variants_per_base=3):
        """Create sets of related records (sharing some fields)"""
        records = []
        for _ in range(base_count):
            # Create base record
            base_url = TestDataFactory.random_url()
            base_username = TestDataFactory.random_email()
            base_password = TestDataFactory.random_password()
            
            # Add base record
            records.append(TestDataFactory.create_data_record(
                url=base_url,
                username=base_username,
                password=base_password
            ))
            
            # Add variants
            for _ in range(variants_per_base):
                variant_type = random.choice(['url', 'username', 'password'])
                if variant_type == 'url':
                    records.append(TestDataFactory.create_data_record(
                        username=base_username,
                        password=base_password
                    ))
                elif variant_type == 'username':
                    records.append(TestDataFactory.create_data_record(
                        url=base_url,
                        password=base_password
                    ))
                else:  # password
                    records.append(TestDataFactory.create_data_record(
                        url=base_url,
                        username=base_username
                    ))
        return records

    @staticmethod
    def create_time_series_data(days=30, records_per_day=(5, 20)):
        """Create time-series data over a period"""
        records = []
        start_date = datetime.utcnow() - timedelta(days=days)
        
        for day in range(days):
            date = start_date + timedelta(days=day)
            count = random.randint(*records_per_day)
            
            day_records = TestDataFactory.create_batch(
                count,
                created_at=date,
                updated_at=date
            )
            records.extend(day_records)
        
        return records

    @staticmethod
    def create_archive_data(num_files=3, records_per_file=(10, 30)):
        """Create mock archive data structure"""
        data = {}
        for i in range(num_files):
            filename = f"data_{TestDataFactory.random_string()}.txt"
            record_count = random.randint(*records_per_file)
            
            records = []
            for _ in range(record_count):
                record = {
                    'url': TestDataFactory.random_url(),
                    'username': TestDataFactory.random_email(),
                    'password': TestDataFactory.random_password()
                }
                records.append(record)
            
            data[filename] = records
        
        return data
