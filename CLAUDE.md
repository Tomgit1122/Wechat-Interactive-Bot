# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a restructured WeChat Work (Enterprise WeChat) bot built with Flask using a layered architecture. The bot supports multi-source data management, processes webhook callbacks, handles text commands, and provides a comprehensive data refresh system with push notification capabilities.

## Architecture

### Layered Structure

- **app/**: Application layer
  - `main.py`: Application entry point and initialization
  - `web/routes.py`: Flask route definitions
  - `web/handlers.py`: Request handlers and message processing logic
  - `adapters/wecom/crypto.py`: WeChat Work encryption/decryption adapter
- **core/**: Business logic layer
  - `model/source.py`: Data source and item models
  - `registry/registry.py`: Multi-source registration and management
  - `refresh/engine.py`: Core refresh engine with atomic operations
- **config/**: Configuration management
  - `settings.py`: Configuration loading and validation
  - `config.json`: WeChat Work credentials and settings
  - `bot_registry.json`: Data source registry (auto-generated)
- **data/**: JSON data directory (whitelist root)
- **scripts/**: Management utilities
  - `manage_bot.py`: Command-line tool for source management

### Message Processing Flow

1. WeChat Work sends webhook to `/wecom/callback`
2. Request signature verification via crypto adapter
3. Message decryption and parsing
4. Command routing to appropriate handlers
5. Business logic execution through refresh engine
6. Response encryption and return

### Multi-Source Data Management

The bot now supports multiple data sources through a registration system:
- **Data Sources**: Configured via registry with `name_key`, `file`, `dot_path`, `enabled` status
- **Registry Management**: Persistent storage in `config/bot_registry.json`
- **Atomic Operations**: Safe read/write operations with temporary files
- **Path Navigation**: Supports complex JSON paths like `a.b[0].c`
- **Pushed State**: Items with `pushed != true` are collected, marked, and returned

## Development Commands

### Run the Application
```bash
python app/main.py
```
The server will start on `0.0.0.0:5000`.

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Data Source Management
```bash
# Register new data source
python scripts/manage_bot.py set <name> <file_path> [--key <dot_path>]

# List all sources
python scripts/manage_bot.py list

# Test refresh functionality
python scripts/manage_bot.py test [--name <source_name>]

# Reset pushed states
python scripts/manage_bot.py reset <source_name|all>
```

### Configuration
Set the `WECOM_CONFIG_FILE` environment variable to specify a custom config file location (default: `config/config.json`).

## WeChat Work Integration

### Required Configuration
- `corp_id`: Enterprise ID (starts with "ww")
- `token`: Verification token  
- `aes_key`: EncodingAESKey (43 characters)
- `agent_id`: Application agent ID
- `bot_registry_file`: Path to source registry file

### Available Commands
- `/refresh`: Refresh all enabled data sources
- `/refresh <source_name>`: Refresh specific data source
- `/bots`: List all registered data sources
- `/reset <source_name|all>`: Reset pushed states for testing

### Security Features
- Path traversal protection with whitelist directories
- Signature verification for all webhook requests
- Message encryption/decryption using WeChat Work crypto
- Configuration validation with masked logging
- Atomic file operations to prevent data corruption

## Key Improvements

1. **Modular Architecture**: Separated concerns across layers
2. **Multi-Source Support**: Register and manage multiple JSON data sources
3. **Enhanced Commands**: More intuitive command structure
4. **Better Error Handling**: Comprehensive error reporting and logging
5. **Management Tools**: Command-line utilities for administration
6. **Extensible Design**: Easy to add new features and data source types