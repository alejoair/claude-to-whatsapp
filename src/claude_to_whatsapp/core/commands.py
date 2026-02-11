"""Command system for bot commands."""

import os
import sys
import subprocess
import logging
from typing import Callable, Dict, List
from dataclasses import dataclass

from ..config import Config

logger = logging.getLogger(__name__)

BOT_PREFIX = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"


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
        """Register a new command.

        Args:
            name: Command name.
            handler: Function to handle the command.
            description: Command description.
        """
        self._commands[name] = Command(name, description, handler)

    def get(self, name: str) -> Command | None:
        """Get a command by name."""
        return self._commands.get(name)

    def list_all(self) -> List[Command]:
        """List all registered commands."""
        return list(self._commands.values())

    def execute(self, name: str, *args, **kwargs) -> str | None:
        """Execute a command.

        Args:
            name: Command name.
            *args: Positional arguments to pass to handler.
            **kwargs: Keyword arguments to pass to handler.

        Returns:
            Result of the command handler, or None if command not found.
        """
        command = self.get(name)
        if command:
            return command.handler(*args, **kwargs)
        return None


# ========== Command handlers ==========

def reload_command(bot, message, client) -> str:
    """Reinicia el bot."""
    import time

    logger.info("Reiniciando bot")

    # Marcar reinicio
    reload_flag = os.path.join(bot.config.bot.data_dir, ".reload_flag")
    with open(reload_flag, "w") as f:
        f.write("reloading")

    bot.shutdown()

    # Reiniciar script
    time.sleep(0.5)
    script_full_path = os.path.abspath(sys.argv[0])
    cmd = f'cd /d "{os.path.dirname(script_full_path)}" && "{sys.executable}" "{script_full_path}"'
    subprocess.Popen(f'cmd /c {cmd}', creationflags=subprocess.CREATE_NEW_CONSOLE)

    return f"{BOT_PREFIX}Reiniciando bot..."


def logout_command(bot, message, client) -> str:
    """Cierra sesión de WhatsApp."""
    logger.info("Comando de logout recibido")

    bot.shutdown()

    # Eliminar sesión
    if os.path.exists(bot.config.whatsapp.db_path):
        try:
            os.remove(bot.config.whatsapp.db_path)
            logger.info("Sesión eliminada")
        except Exception as e:
            logger.error(f"Error eliminando sesión: {e}")

    # Eliminar datos guardados
    bot.config_repo.delete("my_number")
    bot.config_repo.delete("my_jid")
    bot.config_repo.delete("claude_session_id")

    sys.exit(0)


def status_command(bot, message, client) -> str:
    """Muestra estado del bot."""
    session_id = bot.config_repo.get("claude_session_id")
    status = f"Status del Bot:\n"
    status += f"• Número: {bot.my_number}\n"
    status += f"• Session ID: {'Activa' if session_id else 'No existe'}\n"
    status += f"• DB Path: {bot.config.whatsapp.db_path}\n"
    return status


def help_command(bot, message, client) -> str:
    """Muestra ayuda."""
    help_text = f"Comandos disponibles:\n"
    for cmd in bot.command_registry.list_all():
        help_text += f"• BOTSET:{cmd.name} - {cmd.description}\n"
    help_text += f"\nMensajes BOTSYS: son del sistema y se ignoran."
    return help_text
