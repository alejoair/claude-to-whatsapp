# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Python package** called `claude-to-whatsapp` that bridges WhatsApp messaging with Anthropic's Claude AI CLI. The bot receives WhatsApp messages (only from self-messages for security) and forwards them to Claude for intelligent responses, maintaining conversation context across sessions.

**Architecture**: Modular Python package using Neonize for WhatsApp Web API integration.

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Ejecutar el bot
python -m claude_to_whatsapp

# O usando el entry point
claude-to-whatsapp
```

## Architecture

### Data Flow

```
WhatsApp Message -> Neonize Client -> Message Handler -> Claude CLI (via PowerShell) -> Response -> WhatsApp
                                          |
                                  Session Management (SQLite)
                                  Notifications (periodic thread)
```

### Package Structure

```
src/claude_to_whatsapp/
├── __init__.py           # Exportaciones publicas
├── __main__.py          # Entry point para python -m
├── cli.py               # CLI entry point (main)
├── config.py            # Configuracion (dataclasses)
├── logging_config.py     # Configuracion de logging
├── exceptions.py         # Excepciones custom
│
├── core/                # Core business logic
│   ├── bot.py           # WhatsAppBot class (orquestador)
│   ├── models.py        # Data models (dataclasses)
│   └── commands.py      # Sistema de comandos
│
├── integration/          # External integrations
│   ├── base.py          # Interfaces base (ABC)
│   ├── whatsapp.py      # WhatsApp client wrapper (Neonize)
│   └── claude.py        # Claude CLI client wrapper
│
├── events/              # Event handling
│   └── filters.py       # Message filters
│
├── persistence/          # Data persistence
│   └── repositories.py  # Repository pattern (SQLite)
│
└── notifications/        # Periodic notifications
    └── thread.py        # Notification thread
```

### Key Components

**Configuration** (`config.py`)
- `Config` class con configuracion del bot
- Rutas a recursos: `agents_dir`, `skills_dir`, `system_prompt_path`
- Directorio de datos: `~/.claude-to-whatsapp/`

**WhatsApp Integration** (`integration/whatsapp.py`)
- `WhatsAppClient` wrapper sobre `neonize.client.NewClient`
- Metodos: `connect()`, `disconnect()`, `send_message()`, `register_handler()`

**Claude Integration** (`integration/claude.py`)
- `ClaudeClient` wrapper para ejecutar Claude CLI
- Metodo `ask(prompt, session_id)` retorna `(response, new_session_id)`
- Usa PowerShell en Windows

**Session Management** (`persistence/repositories.py`)
- `BotConfigRepository` usando SQLite
- Metodos: `get(key)`, `set(key, value)`, `delete(key)`

**Security Model** (`events/filters.py`)
- `is_self_message()`: Solo responde a mensajes `IsFromMe=True` y `sender==chat`
- `is_system_message()`: Ignora mensajes con prefijo `BOTSYS:`

**Command System** (`core/commands.py`)
- `CommandRegistry` para registrar comandos
- Comandos disponibles: `reload`, `logout`, `status`, `help`

## Configuration

### Runtime Settings

| Componente | Configuracion | Ubicacion |
|------------|---------------|------------|
| Config Python | `Config` dataclass | `config.py` |
| WhatsApp DB | `whatsapp_session.db` | `~/.claude-to-whatsapp/` |
| Bot DB | `bot_data.db` | `~/.claude-to-whatsapp/` |
| Logs | `whatsapp.log` | `~/.claude-to-whatsapp/` |
| System prompt | `system_prompt.txt` | **Directorio actual** |
| Agents | `.claude/agents/*.md` | **Directorio actual** |
| Skills | `.claude/skills/*/` | **Directorio actual** |

### pyproject.toml

- Nombre del paquete: `claude-to-whatsapp`
- Entry points: `claude-to-whatsapp` y `ctw`
- Dependencias: `neonize`, `typer`

## Development Notes

### Message Processing

1. Neonize emite `MessageEv`
2. `MessageFilter.is_self_message()` verifica si es self-message
3. Si es comando `BOTSET:` -> `CommandRegistry.execute()`
4. Si no -> `WhatsAppBot._ask_claude_async()` (thread separado)
5. `NotificationThread` envia notificaciones cada 30s

### Adding New Features

- **Nuevos comandos**: Agregar funcion en `core/commands.py` y registrar en `_register_commands()`
- **Nuevos filtros**: Agregar metodos estaticos en `events/filters.py`
- **Nuevas integraciones**: Crear clase en `integration/` heredando de `MessageClient` o `AIModelClient`

### Type Hints

El codigo usa type hints de Python 3.9+:
- `str | None` para opcionales (PEP 604)
- `list[str]` para listas tipadas

### Resources Importante

**Los recursos NO se empaquetan** con el paquete Python:
- `system_prompt.txt` debe estar en el directorio actual
- `.claude/agents/` debe estar en el directorio actual
- Claude CLI lee estos archivos del directorio actual, no del paquete

## Language

Code comments and UI text are in **Spanish**. Variable names and function names are in **English**.
