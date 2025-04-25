# API Reference

## Overview

Telegram Archive Explorer provides both a Python API and a REST API for integration and extension. This document details both interfaces.

## Python API

### Client Setup

```python
from telegram_archive_explorer import TelegramExplorer, Config

# Initialize with config
config = Config.from_file("config.yaml")
explorer = TelegramExplorer(config)

# Initialize with parameters
explorer = TelegramExplorer(
    api_id="your_api_id",
    api_hash="your_api_hash",
    database_path="path/to/db"
)
```

### Channel Management

```python
# List channels
channels = explorer.channels.list()

# Add channel
explorer.channels.add("@channel_name")

# Remove channel
explorer.channels.remove("@channel_name")

# Get channel status
status = explorer.channels.get_status("@channel_name")
```

### Data Collection

```python
# Collect from specific channel
archives = explorer.collect.from_channel("@channel_name")

# Collect from all channels
archives = explorer.collect.from_all()

# Custom collection options
archives = explorer.collect.from_channel(
    "@channel_name",
    since=datetime(2023, 1, 1),
    until=datetime(2023, 12, 31),
    limit=100
)
```

### Search Operations

```python
# Search by different criteria
results = explorer.search.by_url("example.com")
results = explorer.search.by_username("user123")
results = explorer.search.by_email("user@example.com")

# Advanced search
results = explorer.search.advanced({
    "url": "example.com",
    "date_range": {
        "start": datetime(2023, 1, 1),
        "end": datetime(2023, 12, 31)
    },
    "limit": 100,
    "format": "json"
})
```

### Database Operations

```python
# Direct database access
with explorer.db.connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Messages")
    
# Transaction management
with explorer.db.transaction() as tx:
    tx.execute("INSERT INTO DataEntries ...")
    tx.commit()

# Backup operations
explorer.db.create_backup("backup.db")
explorer.db.restore_backup("backup.db")
```

### Event Handling

```python
# Register event handlers
@explorer.on("archive_collected")
def handle_collection(archive):
    print(f"Collected: {archive.filename}")

@explorer.on("data_extracted")
def handle_extraction(data):
    print(f"Extracted: {data.type}")
```

## REST API

### Authentication

```bash
# Get API token
curl -X POST /api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

### Endpoints

#### Channels

```bash
# List channels
GET /api/v1/channels

# Add channel
POST /api/v1/channels
{
    "name": "@channel_name"
}

# Remove channel
DELETE /api/v1/channels/@channel_name

# Get channel status
GET /api/v1/channels/@channel_name/status
```

#### Collection

```bash
# Start collection
POST /api/v1/collect
{
    "channel": "@channel_name",
    "options": {
        "since": "2023-01-01",
        "until": "2023-12-31",
        "limit": 100
    }
}

# Get collection status
GET /api/v1/collect/status/{job_id}
```

#### Search

```bash
# Search data
POST /api/v1/search
{
    "criteria": {
        "url": "example.com",
        "date_range": {
            "start": "2023-01-01",
            "end": "2023-12-31"
        }
    },
    "options": {
        "limit": 100,
        "format": "json"
    }
}
```

### Response Formats

#### Success Response
```json
{
    "status": "success",
    "data": {},
    "metadata": {
        "timestamp": "2023-01-01T12:00:00Z",
        "request_id": "req_123"
    }
}
```

#### Error Response
```json
{
    "status": "error",
    "error": {
        "code": "ERR_001",
        "message": "Invalid request",
        "details": {}
    },
    "metadata": {
        "timestamp": "2023-01-01T12:00:00Z",
        "request_id": "req_123"
    }
}
```

## WebSocket API

### Connection

```javascript
const ws = new WebSocket('ws://api/v1/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

### Event Subscriptions

```javascript
// Subscribe to events
ws.send(JSON.stringify({
    type: 'subscribe',
    events: ['archive_collected', 'data_extracted']
}));
```

## Extension Points

### Custom Processors

```python
from telegram_archive_explorer import Processor

class CustomProcessor(Processor):
    def process(self, data):
        # Custom processing logic
        return processed_data

# Register processor
explorer.register_processor(CustomProcessor())
```

### Custom Storage Backends

```python
from telegram_archive_explorer import StorageBackend

class CustomStorage(StorageBackend):
    def store(self, data):
        # Custom storage logic
        pass

# Use custom storage
explorer.set_storage(CustomStorage())
```

## Error Handling

### Error Codes

| Code    | Description           | HTTP Status |
|---------|----------------------|-------------|
| ERR_001 | Invalid request      | 400         |
| ERR_002 | Authentication error | 401         |
| ERR_003 | Not found           | 404         |
| ERR_004 | Rate limit exceeded  | 429         |
| ERR_005 | Server error        | 500         |

### Exception Handling

```python
from telegram_archive_explorer import (
    ExplorerError,
    AuthError,
    RateLimitError
)

try:
    explorer.collect.from_channel("@channel")
except AuthError:
    # Handle authentication error
except RateLimitError:
    # Handle rate limiting
except ExplorerError as e:
    # Handle other errors
```

## Rate Limiting

- API calls: 100 requests per minute
- Collection: Based on Telegram API limits
- Search: 10 complex queries per minute

## Best Practices

1. **Error Handling**
   - Always implement proper error handling
   - Use specific exception types
   - Log errors appropriately

2. **Resource Management**
   - Use context managers
   - Close connections properly
   - Implement timeouts

3. **Performance**
   - Use batch operations
   - Implement caching
   - Monitor resource usage

4. **Security**
   - Validate all inputs
   - Use secure connections
   - Implement rate limiting

## See Also
- [Database Schema](database.md)
- [Contributing Guide](contributing.md)
- [Security Guidelines](security.md)
