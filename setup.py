from setuptools import setup, find_packages

setup(
    name="telegram_archive_explorer",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "telethon>=1.28.5",  # Telegram API client
        "sqlalchemy>=2.0.0",  # Database ORM
        "click>=8.1.3",       # CLI interface
        "cryptography>=41.0.0",  # For encryption at rest
        "pysqlcipher3>=1.2.0",   # SQLite encryption support
        "python-dotenv>=1.0.0",  # Environment variable support
        "schedule>=1.2.0",     # For scheduling periodic tasks
    ],
    entry_points={
        "console_scripts": [
            "telegram-explorer=telegram_archive_explorer.cli:main",
        ],
    },
    python_requires=">=3.8",
    description="A tool for exploring and searching Telegram channel archives",
    author="Project Team",
    author_email="info@example.com",
)
