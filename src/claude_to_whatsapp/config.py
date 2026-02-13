"""Configuration management for claude-to-whatsapp."""

import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ClaudeConfig:
    """Claude CLI configuration."""

    timeout: int = 300  # segundos
    output_format: str = "json"
    skip_permissions: bool = True


@dataclass
class WhatsAppConfig:
    """WhatsApp configuration."""

    db_path: str = None  # Se setea en Config
    log_path: str = None  # Se setea en Config


@dataclass
class BotConfig:
    """Bot configuration."""

    data_dir: str = None  # Se setea en Config
    notification_interval: int = 30


@dataclass
class Config:
    """Main configuration for the bot."""

    work_dir: str
    claude: ClaudeConfig
    whatsapp: WhatsAppConfig
    bot: BotConfig

    def __init__(self, work_dir: str = None):
        """Initialize configuration.

        Args:
            work_dir: Working directory where .claude/ and system_prompt.txt are.
                      Defaults to current directory.
        """
        self.work_dir = work_dir or os.getcwd()

        # Directorio de datos del bot (~/.claude-to-whatsapp/)
        home = os.path.expanduser("~")
        data_dir = os.path.join(home, ".claude-to-whatsapp")
        os.makedirs(data_dir, exist_ok=True)

        # Configurar sub-configuraciones
        self.claude = ClaudeConfig()
        self.whatsapp = WhatsAppConfig(
            db_path=os.path.join(data_dir, "whatsapp_session.db"),
            log_path=os.path.join(data_dir, "whatsapp.log"),
        )
        self.bot = BotConfig(
            data_dir=data_dir,
            notification_interval=30,
        )

    @property
    def agents_dir(self) -> str:
        """Path to .claude/agents/ in working directory."""
        return os.path.join(self.work_dir, ".claude", "agents")

    @property
    def skills_dir(self) -> str:
        """Path to .claude/skills/ in working directory."""
        return os.path.join(self.work_dir, ".claude", "skills")

    @property
    def system_prompt_path(self) -> str:
        """Path to system_prompt.txt in working directory."""
        return os.path.join(self.work_dir, "system_prompt.txt")

    def set_work_dir(self, path: str) -> bool:
        """Set a new working directory.

        Args:
            path: New working directory path (can be relative or absolute).

        Returns:
            True if work_dir was changed successfully, False otherwise.
        """
        # Convertir a ruta absoluta y normalizar
        new_path = os.path.abspath(os.path.expanduser(path))

        # Validar que existe y es directorio
        if not os.path.isdir(new_path):
            return False

        self.work_dir = new_path
        return True
