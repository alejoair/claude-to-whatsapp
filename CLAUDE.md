# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **WhatsApp bot** that bridges WhatsApp messaging with Anthropic's Claude AI CLI. The bot receives WhatsApp messages (only from the owner's number for security) and forwards them to Claude for intelligent responses, maintaining conversation context across sessions.

**Architecture**: Single-file Python application (`whatsapp_bot.py`) using event-driven architecture with the Neonize library for WhatsApp Web API integration.

## Prerequisites

- Python 3.x
- Claude CLI installed and available in PATH
- PowerShell (Windows-specific implementation)

## Installation and Setup

```bash
# Install the Neonize dependency
pip install neonize

# Run the bot
python whatsapp_bot.py
```

**First run**: The bot will display a QR code to scan with WhatsApp mobile app for pairing. Subsequent runs use saved credentials.

## Architecture

### Data Flow

```
WhatsApp Message → Neonize Client → Message Handler → Claude CLI (via PowerShell) → Response → WhatsApp
                                          ↓
                                  Session Management (JSON)
```

### Key Components

**WhatsApp Integration** (`whatsapp_bot.py:22-23`)
- Uses `neonize.client.NewClient` for WhatsApp Web API
- Session persistence via SQLite database (`whatsapp_session.db`)
- Event-driven: `ConnectedEv`, `PairStatusEv`, `MessageEv`, `HistorySyncEv`

**Claude Integration** (`ask_claude()` function, line 52)
- Invokes Claude CLI via PowerShell subprocess
- Uses `--output-format json` for structured responses
- Supports session-based conversations (`-r` flag for existing sessions, `-p` for new)
- 120-second timeout for Claude responses

**Session Management** (`load_sessions()`/`save_sessions()`, lines 32-49)
- Maps WhatsApp chat JIDs to Claude session IDs in `claude_sessions.json`
- Enables multi-turn conversations with context persistence

**Security Model** (line 130-132)
- Bot only responds to messages from the owner's number (`MY_NUMBER`)
- Captured during pairing from `PairStatusEv`
- All other messages are logged and ignored

## Configuration

### Runtime Settings (Hardcoded)

| Setting | Location | Purpose |
|---------|----------|---------|
| `DB_PATH` | Line 26 | WhatsApp session database (`whatsapp_session.db`) |
| `SESSIONS_FILE` | Line 27 | Claude session mappings (`claude_sessions.json`) |
| Log file | Line 16 | Activity log (`whatsapp.log`) |
| Timeout | Line 77 | Claude CLI response timeout (120 seconds) |

### Generated Files

- `whatsapp_session.db` - SQLite database with WhatsApp credentials
- `claude_sessions.json` - Session ID mappings per chat
- `whatsapp.log` - Application logs with UTF-8 encoding

## Development Notes

### Windows-Specific Implementation

The bot uses PowerShell for subprocess execution (line 73-74). For Linux/macOS compatibility, replace:
```python
result = subprocess.run(
    ["powershell", "-Command", ps_script],
    ...
)
```
with direct shell invocation.

### Message Processing

Messages are extracted from WhatsApp's protocol message structure (lines 138-147):
- `msg.conversation` - Standard text messages
- `msg.extendedTextMessage.text` - Extended text messages
- `msg.protocolMessage` - System messages (ignored)

### Event Handlers

- `on_connected()` (line 102): Connection established
- `on_pair_status()` (line 107): Captures owner's phone number on pairing
- `on_history_sync()` (line 117): Chat history synchronization
- `on_message()` (line 122): Main message processing logic

### Adding New Features

- **Multi-user support**: Remove the `MY_NUMBER` check or add allowlist logic
- **Additional commands**: Extend `on_message()` to handle command prefixes
- **Rate limiting**: Add throttling in `on_message()` before calling `ask_claude()`
- **Async processing**: Convert blocking `ask_claude()` calls to async/await

## Language

Code comments and UI text are in **Spanish**. Variable names and function names are in English.
