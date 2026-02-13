"""Command system for bot commands."""

import os
import sys
import subprocess
import logging
import hashlib
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


def _get_work_dir_hash(work_dir: str) -> str:
    """Genera un hash único para un work_dir."""
    return hashlib.md5(work_dir.encode()).hexdigest()


def _get_session_key(work_dir: str) -> str:
    """Obtiene la clave para almacenar session_id de un work_dir."""
    return f"claude_session_id:{_get_work_dir_hash(work_dir)}"


def _clear_session_for_workdir(bot, work_dir: str) -> None:
    """Limpia el session_id para un work_dir específico."""
    session_key = _get_session_key(work_dir)
    bot.config_repo.delete(session_key)


def workdir_command(bot, message, client, command_text: str = "") -> str:
    """Cambia la carpeta de trabajo."""
    # Extraer ruta del comando: "workdir /ruta" o "cd /ruta"
    # command_text ya está sin el prefijo "BOTSET:"
    text = command_text.strip().lower()

    if not text:
        return f"{BOT_PREFIX}Error: Comando vacío"

    # Obtener nombre del comando y argumentos
    parts = text.split(maxsplit=1)
    cmd_name = parts[0]
    path_arg = parts[1].strip() if len(parts) > 1 else ""

    # Solo workdir o cd son válidos
    if cmd_name not in ("workdir", "cd"):
        return f"{BOT_PREFIX}Comando desconocido"

    if not path_arg:
        # Sin argumentos, mostrar work_dir actual
        return f"{BOT_PREFIX}Carpeta actual:\n{bot.config.work_dir}"

    # Guardar session_id del work_dir actual antes de cambiar
    old_work_dir = bot.config.work_dir
    current_session_id = bot.config_repo.get("claude_session_id")
    if current_session_id:
        old_session_key = _get_session_key(old_work_dir)
        bot.config_repo.set(old_session_key, current_session_id)

    # Intentar cambiar work_dir
    if not bot.config.set_work_dir(path_arg):
        return f"{BOT_PREFIX}Error: La ruta '{path_arg}' no existe o no es un directorio"

    new_work_dir = bot.config.work_dir

    # Validar recursos (system_prompt.txt debe existir)
    if not os.path.exists(bot.config.system_prompt_path):
        # Revertir cambio
        bot.config.work_dir = old_work_dir
        return f"{BOT_PREFIX}Error: No se encontró system_prompt.txt en '{new_work_dir}'"

    # Recargar recursos
    if not bot.reload_resources():
        # Revertir cambio
        bot.config.work_dir = old_work_dir
        bot.reload_resources()  # Recargar recursos originales
        return f"{BOT_PREFIX}Error: No se pudieron recargar los recursos"

    # Cargar session_id para el nuevo work_dir
    new_session_key = _get_session_key(new_work_dir)
    new_session_id = bot.config_repo.get(new_session_key)

    # Actualizar session_id activo
    if new_session_id:
        bot.config_repo.set("claude_session_id", new_session_id)
    else:
        # No hay session_id para este work_dir, limpiar el actual
        bot.config_repo.delete("claude_session_id")

    logger.info(f"📂 Work_dir cambiado: {old_work_dir} -> {new_work_dir}")

    response = f"{BOT_PREFIX}Carpeta de trabajo cambiada\n\n"
    response += f"📂 Nueva ruta: {new_work_dir}\n"
    if new_session_id:
        response += f"🔄 Sesión restaurada\n"
    else:
        response += f"🆕 Nueva sesión iniciada\n"
    response += f"📜 System prompt recargado"

    return response


def help_command(bot, message, client) -> str:
    """Muestra ayuda."""
    help_text = f"Comandos disponibles:\n"
    for cmd in bot.command_registry.list_all():
        help_text += f"• BOTSET:{cmd.name} - {cmd.description}\n"
    help_text += "\nMensajes BOTSYS: son del sistema y se ignoran."
    return help_text
