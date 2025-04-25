# Telegram Archive Explorer

A tool for collecting, parsing, and searching data from Telegram channel archives.

## Features

- Connect to Telegram channels and download archive files
- Extract and parse various archive formats (ZIP, RAR, 7z, etc.)
- Parse data files into structured records
- Store parsed data in an encrypted SQLite database
- Search data by URL, email, username, or password
- Schedule periodic archive collection
- Command-line interface for all operations

## Installation

### Requirements

- Python 3.8+
- SQLite3
- Optional: 7zip, unrar (for additional archive format support)

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/telegram-archive-explorer.git
cd telegram-archive-explorer

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package and dependencies
pip install -e .
```

## Setup

Before using Telegram Archive Explorer, you need to set up your Telegram API credentials:

1. Visit https://my.telegram.org and log in with your Telegram account
2. Go to "API development tools" and create a new application
3. Note your API ID and API hash
4. Run the setup command:

```bash
telegram-explorer setup
```

Follow the prompts to enter your API credentials and configure database encryption.

## Usage

### Managing Channels

```bash
# List configured channels
telegram-explorer channels --list

# Add a channel to monitor
telegram-explorer channels --add @channel_name

# Remove a channel
telegram-explorer channels --remove @channel_name
```

### Collecting Archives

```bash
# Collect archives from a specific channel
telegram-explorer collect --channel @channel_name

# Collect archives from all configured channels
telegram-explorer collect --all
```

### Searching Data

```bash
# Search for a URL
telegram-explorer search --url "example.com"

# Search for a username or email
telegram-explorer search --username "user*"

# Search for a password
telegram-explorer search --password "pass123"

# Output format options
telegram-explorer search --url "example.com" --format json
telegram-explorer search --url "example.com" --format csv
telegram-explorer search --url "example.com" --format table
```

## Scheduler

The scheduler can automatically collect archives from configured channels at regular intervals:

```bash
# Start the scheduler in the background
telegram-explorer scheduler --start --daemon

# Stop the scheduler
telegram-explorer scheduler --stop

# Run collection immediately
telegram-explorer scheduler --run-now

# Check scheduler status
telegram-explorer scheduler --status
```

## Security

This tool supports database encryption to protect sensitive data:

- Encryption is enabled by default during setup
- Password protection for the database
- Data is stored encrypted at rest

## License

This project is licensed under the MIT License - see the LICENSE file for details.
