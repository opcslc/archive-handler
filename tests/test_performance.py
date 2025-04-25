import pytest
from telegram_archive_explorer.database import DataRecord

def test_bulk_insert_performance(test_db, large_dataset, benchmark):
    """Test performance of bulk inserting records"""
    def do_bulk_insert():
        records = [
            DataRecord(
                url=item['url'],
                username=item['username'],
                password=item['password']
            ) for item in large_dataset
        ]
        test_db.bulk_save_objects(records)
        test_db.commit()
    
    benchmark(do_bulk_insert)
    assert test_db.query(DataRecord).count() == len(large_dataset)

def test_search_performance(test_db, large_dataset, search_engine, benchmark):
    """Test search performance with large dataset"""
    # Setup: Insert test data
    records = [
        DataRecord(
            url=item['url'],
            username=item['username'],
            password=item['password']
        ) for item in large_dataset
    ]
    test_db.bulk_save_objects(records)
    test_db.commit()
    
    # Test URL search performance
    def search_urls():
        results = search_engine.search_by_url("example", use_wildcards=True)
        return list(results)
    benchmark(search_urls)
    
    # Test username search performance
    def search_usernames():
        results = search_engine.search_by_username("user", use_wildcards=True)
        return list(results)
    benchmark(search_usernames)

@pytest.mark.timeout(300)
def test_duplicate_handling_performance(test_db, large_dataset, data_importer, benchmark):
    """Test duplicate detection and handling performance"""
    # First insertion
    records1 = [
        DataRecord(
            url=item['url'],
            username=item['username'],
            password=item['password']
        ) for item in large_dataset
    ]
    test_db.bulk_save_objects(records1)
    test_db.commit()
    
    # Create duplicate records with some modifications
    duplicate_data = large_dataset[:5000]  # 50% duplicates
    new_data = [
        {
            'url': f'http://newexample{i}.com',
            'username': f'newuser{i}@example.com',
            'password': f'newpassword{i}'
        } for i in range(5000, 10000)
    ]
    mixed_data = duplicate_data + new_data
    
    def import_with_dupes():
        data_importer.import_records(mixed_data)
    
    benchmark(import_with_dupes)
    
    # Verify results
    total_records = test_db.query(DataRecord).count()
    assert total_records == 15000  # Original 10000 + 5000 new

@pytest.mark.asyncio
async def test_encryption_performance(test_db, large_dataset, benchmark):
    """Test encryption/decryption performance with large datasets"""
    from telegram_archive_explorer.database import encrypt_data, decrypt_data
    
    test_data = "sensitive_data" * 1000  # Large string to encrypt
    
    def encryption_benchmark():
        for _ in range(100):
            encrypted = encrypt_data(test_data)
            decrypted = decrypt_data(encrypted)
            assert decrypted == test_data
    
    benchmark(encryption_benchmark)
