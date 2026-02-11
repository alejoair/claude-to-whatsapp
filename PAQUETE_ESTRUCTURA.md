# Estructura del Paquete Python: claude-to-whatsapp

> Paquete instalable de Python que integra WhatsApp con Claude AI CLI.

## Resumen

Este documento describe la estructura del paquete Python `claude-to-whatsapp`, un bot que conecta WhatsApp con Claude AI CLI.

## Instalación

```bash
# Desde PyPI (futuro)
pip install claude-to-whatsapp

# En modo desarrollo (editable)
pip install -e .
```

## Comandos

```bash
# Iniciar el bot
claude-to-whatsapp run

# Configurar el bot
claude-to-whatsapp configure

# Ver estado
claude-to-whatsapp status

# Cerrar sesión
claude-to-whatsapp logout

# Ayuda
claude-to-whatsapp --help
```

---

## Estructura del Proyecto

```
claude-to-whatsapp/
├── pyproject.toml                    # Configuración del paquete (PEP 621)
├── README.md                         # Documentación principal
├── CHANGELOG.md                      # Historial de cambios
├── LICENSE                           # Licencia (MIT)
├── .gitignore
│
├── src/                              # Código fuente del paquete
│   └── claude_to_whatsapp/
│       ├── __init__.py               # Exportaciones públicas
│       ├── __version__.py            # Versión del paquete
│       │
│       ├── cli.py                    # CLI entry point (Typer)
│       ├── config.py                 # Configuración (Pydantic)
│       ├── logging_config.py         # Configuración de logging
│       ├── exceptions.py             # Excepciones custom
│       │
│       ├── core/                     # Core business logic
│       │   ├── __init__.py
│       │   ├── bot.py                # WhatsAppBot class (orquestador)
│       │   ├── models.py             # Data models (Pydantic)
│       │   └── commands.py           # Sistema de comandos
│       │
│       ├── integration/              # External integrations
│       │   ├── __init__.py
│       │   ├── base.py               # Interfaces base (ABC)
│       │   ├── whatsapp.py           # WhatsApp client wrapper
│       │   └── claude.py             # Claude CLI client wrapper
│       │
│       ├── events/                   # Event handling
│       │   ├── __init__.py
│       │   ├── observer.py           # Event bus
│       │   ├── handlers.py           # Event handlers (Neonize)
│       │   └── filters.py            # Message filters
│       │
│       ├── persistence/               # Data persistence
│       │   ├── __init__.py
│       │   ├── database.py           # DB connection manager
│       │   └── repositories.py       # Repository pattern
│       │
│       ├── notifications/            # Periodic notifications
│       │   ├── __init__.py
│       │   └── thread.py             # Notification thread
│       │
│       └── resources/               # Package resources (importlib.resources)
│           ├── __init__.py
│           ├── loader.py             # Resource loader
│           ├── system_prompt.txt     # System prompt default
│           ├── agents/               # Agent definitions (.md)
│           │   └── *.md
│           └── skills/               # Skill definitions
│               └── */
│
├── tests/                            # Suite de pruebas
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_core/
│   │   ├── test_bot.py
│   │   ├── test_models.py
│   │   └── test_commands.py
│   ├── test_integration/
│   │   ├── test_whatsapp.py
│   │   └── test_claude.py
│   ├── test_events/
│   │   ├── test_handlers.py
│   │   └── test_filters.py
│   ├── test_persistence/
│   │   ├── test_database.py
│   │   └── test_repositories.py
│   └── fixtures/
│       ├── sample_messages.json
│       └── sample_agents.json
│
└── docs/                             # Documentación (Sphinx)
    ├── conf.py
    ├── index.rst
    ├── modules.rst
    └── api/
```

---

## Descripción de Componentes

### `pyproject.toml`

Configuración moderna del paquete (PEP 621):

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "claude-to-whatsapp"
version = "0.1.0"
description = "WhatsApp bot con integración a Claude AI CLI"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "your@email.com"}]

dependencies = [
    "neonize>=0.1.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "typer>=0.9.0",
    "structlog>=23.0.0",
]

[project.scripts]
claude-to-whatsapp = "claude_to_whatsapp.cli:main"
ctw = "claude_to_whatsapp.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.10.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
    "sphinx>=7.0.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]
```

---

### `src/claude_to_whatsapp/__init__.py`

Exportaciones públicas del paquete:

```python
"""claude-to-whatsapp: WhatsApp bot with Claude AI integration."""

from claude_to_whatsapp.core.bot import WhatsAppBot
from claude_to_whatsapp.config import Config, ClaudeConfig
from claude_to_whatsapp.exceptions import (
    ClaudeTimeoutError,
    ClaudeConnectionError,
    WhatsAppConnectionError,
)

__version__ = "0.1.0"
__all__ = [
    "WhatsAppBot",
    "Config",
    "ClaudeConfig",
    "ClaudeTimeoutError",
    "ClaudeConnectionError",
    "WhatsAppConnectionError",
    "__version__",
]
```

---

### `src/claude_to_whatsapp/cli.py`

CLI principal usando Typer:

```python
"""CLI entry point for claude-to-whatsapp."""

import typer
from .config import load_config
from .core.bot import WhatsAppBot
from .logging_config import configure_logging

app = typer.Typer(
    name="claude-to-whatsapp",
    help="WhatsApp bot con integración a Claude AI CLI",
    no_args_is_help=True,
)

@app.command()
def run(
    config: str = typer.Option(
        "~/.claude-to-whatsapp/config.yaml",
        "--config", "-c",
        help="Ruta al archivo de configuración"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Mostrar logs detallados"
    )
):
    """Inicia el bot de WhatsApp."""
    configure_logging("DEBUG" if verbose else "INFO")
    config_obj = load_config(config)
    bot = WhatsAppBot(config_obj)
    bot.run()

@app.command()
def configure():
    """Configura el bot (interactivo)."""
    typer.echo("Configurando claude-to-whatsapp...")
    # Implementar configuración interactiva

@app.command()
def status():
    """Muestra el estado del bot."""
    # Implementar comando de estado

@app.command()
def logout():
    """Cierra la sesión de WhatsApp y elimina credenciales."""
    # Implementar comando de logout

def main():
    app()

if __name__ == "__main__":
    main()
```

---

### `src/claude_to_whatsapp/config.py`

Configuración usando Pydantic:

```python
"""Configuration management using Pydantic."""

from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
from pathlib import Path

class ClaudeConfig(BaseSettings):
    """Claude CLI configuration."""

    cli_path: str = Field(default="claude", description="Path to Claude CLI")
    timeout: int = Field(default=300, gt=0, description="Timeout in seconds")
    output_format: str = Field(default="json", description="Output format")
    skip_permissions: bool = Field(default=True, description="Skip permissions prompts")

    class Config:
        env_prefix = "CLAUDE_"


class WhatsAppConfig(BaseSettings):
    """WhatsApp configuration."""

    db_path: str = Field(
        default="~/.claude-to-whatsapp/whatsapp_session.db",
        description="Path to WhatsApp session database"
    )
    log_path: str = Field(
        default="~/.claude-to-whatsapp/whatsapp.log",
        description="Path to log file"
    )

    class Config:
        env_prefix = "WHATSAPP_"


class BotConfig(BaseSettings):
    """Bot configuration."""

    data_dir: str = Field(
        default="~/.claude-to-whatsapp",
        description="Directory for bot data"
    )
    notification_interval: int = Field(
        default=30,
        gt=0,
        description="Notification interval in seconds"
    )

    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)

    class Config:
        env_prefix = "BOT_"


def load_config(path: str) -> BotConfig:
    """Load configuration from file or environment variables."""
    return BotConfig()
```

---

### `src/claude_to_whatsapp/core/bot.py`

Clase principal del bot:

```python
"""Main WhatsAppBot class."""

from typing import Optional
from ..config import BotConfig
from ..integration.whatsapp import WhatsAppClient
from ..integration.claude import ClaudeClient
from ..persistence.repositories import BotConfigRepository
from ..notifications.thread import NotificationThread
from .commands import CommandRegistry

class WhatsAppBot:
    """Main bot class orchestrating all components."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.whatsapp_client = WhatsAppClient(config.whatsapp)
        self.claude_client = ClaudeClient(config.claude)
        self.config_repo = BotConfigRepository(config.data_dir)
        self.notification_thread = NotificationThread(config.notification_interval)
        self.command_registry = CommandRegistry()

    def run(self) -> None:
        """Run the bot main loop."""
        # Register command handlers
        self._register_commands()

        # Connect to WhatsApp
        self.whatsapp_client.connect()

        # Start notification thread
        self.notification_thread.start()

        # Main loop
        self._main_loop()

    def _register_commands(self) -> None:
        """Register bot commands."""
        from .commands import reload_command, logout_command, status_command, help_command
        self.command_registry.register("reload", reload_command)
        self.command_registry.register("logout", logout_command)
        self.command_registry.register("status", status_command)
        self.command_registry.register("help", help_command)

    def _main_loop(self) -> None:
        """Main bot loop."""
        import signal
        import time

        def signal_handler(signum, frame):
            self.shutdown()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self) -> None:
        """Gracefully shutdown the bot."""
        self.notification_thread.stop()
        self.whatsapp_client.disconnect()
```

---

### `src/claude_to_whatsapp/integration/base.py`

Interfaces base (ABC):

```python
"""Base interfaces for integrations."""

from abc import ABC, abstractmethod
from typing import Optional, Any

class MessageClient(ABC):
    """Base interface for message clients."""

    @abstractmethod
    def connect(self) -> None:
        """Connect to the message service."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the message service."""
        pass

    @abstractmethod
    def send_message(self, recipient: Any, message: str) -> None:
        """Send a message to a recipient."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        pass


class AIModelClient(ABC):
    """Base interface for AI model clients."""

    @abstractmethod
    def ask(self, prompt: str, session_id: Optional[str] = None) -> tuple[str, str]:
        """Ask the AI model a prompt.

        Returns:
            Tuple of (response, new_session_id)
        """
        pass
```

---

### `src/claude_to_whatsapp/integration/whatsapp.py`

Cliente WhatsApp:

```python
"""WhatsApp client wrapper using Neonize."""

from typing import Optional
from neonize.client import NewClient
from neonize.events import ConnectedEv, PairStatusEv, MessageEv, HistorySyncEv
from .base import MessageClient

class WhatsAppClient(MessageClient):
    """WhatsApp client wrapper."""

    def __init__(self, config: WhatsAppConfig):
        self.config = config
        self._client = None
        self._handlers = {}

    def connect(self) -> None:
        """Connect to WhatsApp."""
        db_path = Path(self.config.db_path).expanduser()
        self._client = NewClient(str(db_path))
        self._client.connect()

    def disconnect(self) -> None:
        """Disconnect from WhatsApp."""
        if self._client:
            self._client.disconnect()

    def send_message(self, recipient: Any, message: str) -> None:
        """Send a message to a recipient."""
        if self._client:
            self._client.send_message(recipient, message)

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._client is not None

    def register_handler(self, event_type, handler: callable) -> None:
        """Register an event handler."""
        if self._client:
            self._client.event(event_type)(handler)
```

---

### `src/claude_to_whatsapp/integration/claude.py`

Cliente Claude CLI:

```python
"""Claude CLI client wrapper."""

from typing import Optional, Tuple
import subprocess
import json
from .base import AIModelClient

class ClaudeClient(AIModelClient):
    """Claude CLI client wrapper."""

    def __init__(self, config: ClaudeConfig):
        self.config = config

    def ask(self, prompt: str, session_id: Optional[str] = None) -> Tuple[str, str]:
        """Ask Claude a prompt.

        Returns:
            Tuple of (response, new_session_id)
        """
        cmd = self._build_command(prompt, session_id)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                encoding="utf-8"
            )

            response = json.loads(result.stdout)
            return response.get("result", ""), response.get("session_id", "")

        except subprocess.TimeoutExpired:
            raise ClaudeTimeoutError(f"Timeout after {self.config.timeout}s")
        except json.JSONDecodeError as e:
            raise ClaudeConnectionError(f"Invalid JSON response: {e}")

    def _build_command(self, prompt: str, session_id: Optional[str]) -> list[str]:
        """Build the Claude CLI command."""
        base_cmd = [self.config.cli_path]
        base_cmd.extend(["--output-format", self.config.output_format])

        if self.config.skip_permissions:
            base_cmd.append("--dangerously-skip-permissions")

        if session_id:
            base_cmd.extend(["-r", session_id])
        else:
            base_cmd.append("-p")

        base_cmd.append(prompt)
        return base_cmd
```

---

### `src/claude_to_whatsapp/persistence/repositories.py`

Repository pattern para persistencia:

```python
"""Repositories for data persistence."""

from abc import ABC, abstractmethod
from typing import Optional
import sqlite3
from pathlib import Path

class BotConfigRepository(ABC):
    """Base repository for bot configuration."""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a configuration value."""
        pass

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Set a configuration value."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a configuration value."""
        pass


class SQLiteBotConfigRepository(BotConfigRepository):
    """SQLite implementation of BotConfigRepository."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path).expanduser()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def get(self, key: str) -> Optional[str]:
        """Get a configuration value."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM bot_config WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def set(self, key: str, value: str) -> None:
        """Set a configuration value."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO bot_config (key, value) VALUES (?, ?)",
                (key, value)
            )
            conn.commit()

    def delete(self, key: str) -> None:
        """Delete a configuration value."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM bot_config WHERE key = ?",
                (key,)
            )
            conn.commit()
```

---

### `src/claude_to_whatsapp/core/commands.py`

Sistema de comandos:

```python
"""Command system for the bot."""

from typing import Callable, Dict, List
from dataclasses import dataclass

@dataclass
class Command:
    """Represents a bot command."""

    name: str
    description: str
    handler: Callable

class CommandRegistry:
    """Registry for bot commands."""

    def __init__(self):
        self._commands: Dict[str, Command] = {}

    def register(self, name: str, handler: Callable, description: str = "") -> None:
        """Register a new command."""
        self._commands[name] = Command(name, description, handler)

    def get(self, name: str) -> Optional[Command]:
        """Get a command by name."""
        return self._commands.get(name)

    def list_all(self) -> List[Command]:
        """List all registered commands."""
        return list(self._commands.values())

    def execute(self, name: str, *args, **kwargs) -> Optional[str]:
        """Execute a command."""
        command = self.get(name)
        if command:
            return command.handler(*args, **kwargs)
        return None


# Command handlers
def reload_command(bot: WhatsAppBot, args: List[str]) -> str:
    """Reload the bot."""
    bot.reload()
    return "Reiniciando bot..."

def logout_command(bot: WhatsAppBot, args: List[str]) -> str:
    """Logout from WhatsApp."""
    bot.logout()
    return "Sesión cerrada..."

def status_command(bot: WhatsAppBot, args: List[str]) -> str:
    """Show bot status."""
    return f"Status: Connected={bot.whatsapp_client.is_connected()}"

def help_command(bot: WhatsAppBot, args: List[str]) -> str:
    """Show help message."""
    commands = bot.command_registry.list_all()
    help_text = "Comandos disponibles:\n"
    for cmd in commands:
        help_text += f"  BOTSET:{cmd.name} - {cmd.description}\n"
    return help_text
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        claude-to-whatsapp                            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │      CLI (typer)   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   WhatsAppBot     │
                    │   (core/bot.py)    │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│ WhatsAppClient │  │  ClaudeClient  │  │ ConfigRepo     │
│ (integration/) │  │ (integration/) │  │ (persistence/) │
└────────────────┘  └────────────────┘  └────────────────┘
        │                     │
        │              ┌──────▼────────┐
        │              │ subprocess    │
        │              │ (claude CLI)  │
        │              └───────────────┘
        │
┌───────▼────────┐
│   Neonize       │
│   (external)    │
└────────────────┘
```

---

## Event Flow

```
MessageEv (Neonize)
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Check filters (events/filters.py)                           │
│     - IsFromMe == True                                          │
│     - sender == chat                                             │
│     - Not BOTSYS: prefix                                         │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Check for BOTSET: commands (core/commands.py)              │
│     - reload, logout, status, help                              │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼ (if not a command)
┌─────────────────────────────────────────────────────────────────┐
│  3. Send to Claude (async thread)                               │
│     - Register in pending_requests                               │
│     - Call ClaudeClient.ask()                                   │
│     - Start notification thread                                  │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Claude response received                                     │
│     - Save session_id                                           │
│     - Send to WhatsApp                                           │
│     - Clean up pending_requests                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directorios de Datos

| Directorio | Contenido | Ubicación |
|------------|-----------|-----------|
| `~/.claude-to-whatsapp/` | Datos del bot | Runtime |
| `src/claude_to_whatsapp/resources/` | Recursos del paquete | Distribución |
| `~/.claude-to-whatsapp/whatsapp_session.db` | Sesión WhatsApp | Runtime |
| `~/.claude-to-whatsapp/bot_data.db` | Configuración bot | Runtime |
| `~/.claude-to-whatsapp/whatsapp.log` | Logs | Runtime |

---

## Archivos de Configuración

### `config.yaml` (opcional)

```yaml
claude:
  timeout: 300
  skip_permissions: true

whatsapp:
  db_path: ~/.claude-to-whatsapp/whatsapp_session.db
  log_path: ~/.claude-to-whatsapp/whatsapp.log

bot:
  notification_interval: 30
```

---

## Notas de Implementación

1. **Type Hints**: Todo el código debe tener type hints completos.
2. **Docstrings**: Todos los módulos, clases y funciones deben tener docstrings (Google/Numpy style).
3. **Logging**: Usar `structlog` para logging estructurado.
4. **Tests**: Cobertura mínima de 80% para código de producción.
5. **Linting**: Usar `ruff` para linting y formatting.
6. **Type Checking**: Usar `mypy` para type checking.

---

## Roadmap de Migración

1. ✅ Crear estructura de directorios
2. ✅ Crear `pyproject.toml`
3. ✅ Migrar configuración a `config.py`
4. ✅ Crear wrappers de integración
5. ✅ Migrar lógica del bot
6. ✅ Mover recursos al paquete
7. ✅ Crear CLI
8. ✅ Agregar tests
9. ✅ Documentación
10. ✅ Release v0.1.0
