"""Claude CLI client wrapper."""

import subprocess
import json
import logging
import platform
import shlex
from typing import Optional, Tuple
from .base import AIModelClient
from ..exceptions import ClaudeTimeoutError, ClaudeConnectionError

logger = logging.getLogger(__name__)


class ClaudeClient(AIModelClient):
    """Claude CLI client wrapper."""

    def __init__(self, timeout: int = 300, skip_permissions: bool = True):
        """Initialize Claude client.

        Args:
            timeout: Timeout in seconds for Claude CLI response.
            skip_permissions: Skip permission prompts.
        """
        self.timeout = timeout
        self.skip_permissions = skip_permissions

    def ask(self, prompt: str, session_id: Optional[str] = None, agents: Optional[str] = None, system_prompt_file: Optional[str] = None) -> Tuple[str, str]:
        """Ask Claude a prompt.

        Args:
            prompt: The prompt to send to Claude.
            session_id: Session ID to continue conversation. If None, creates new session.
            agents: JSON string with agents configuration.
            system_prompt_file: Path to system prompt file.

        Returns:
            Tuple of (response, new_session_id).

        Raises:
            ClaudeTimeoutError: If Claude CLI times out.
            ClaudeConnectionError: If there's an error communicating with Claude.
        """
        cmd = self._build_command(prompt, session_id, agents, system_prompt_file)

        try:
            logger.info(f"🤖 Enviando a Claude: {prompt[:50]}...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
            )

            # Si el session_id guardado no existe, reintentar sin él
            if result.returncode != 0 and session_id and "No conversation found" in result.stderr:
                logger.warning("⚠️ Session ID no encontrado, creando nueva sesión...")
                cmd = self._build_command(prompt, None, agents, system_prompt_file)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    encoding="utf-8",
                )

            # Verificar si hay salida
            if not result.stdout:
                error_msg = result.stderr or "Empty response from Claude"
                logger.error(f"❌ Error de Claude: {error_msg}")
                raise ClaudeConnectionError(error_msg)

            # Parsear JSON
            response = json.loads(result.stdout)
            return response.get("result", ""), response.get("session_id", "")

        except subprocess.TimeoutExpired:
            logger.error("⏱️ Timeout esperando respuesta de Claude")
            raise ClaudeTimeoutError(f"Timeout después de {self.timeout}s")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parseando JSON de Claude: {e}")
            raise ClaudeConnectionError(f"Invalid JSON response: {e}")

    def _build_command(self, prompt: str, session_id: Optional[str], agents: Optional[str], system_prompt_file: Optional[str]) -> list[str]:
        """Build Claude CLI command.

        Args:
            prompt: The prompt to send to Claude.
            session_id: Session ID for existing conversation.
            agents: JSON string with agents configuration.
            system_prompt_file: Path to system prompt file.

        Returns:
            List of command arguments.
        """
        # Escapar el prompt de forma segura con shlex
        safe_prompt = shlex.quote(prompt)

        # Construir comando base
        cmd_str = f"claude --output-format json --permission-mode bypassPermissions -p {safe_prompt}"

        # Agregar system_prompt_file si existe
        # NOTA: Si hay system_prompt_file, NO usar session_id porque -r ignora el nuevo system_prompt
        if system_prompt_file:
            safe_file = shlex.quote(system_prompt_file)
            cmd_str += f" --system-prompt-file {safe_file}"
        # Solo usar session_id si NO hay system_prompt_file (para resumir sesión anterior)
        elif session_id:
            cmd_str += f" -r {shlex.quote(session_id)}"

        # Agregar agents si existe
        if agents:
            # Escapar el JSON para shell
            safe_agents = shlex.quote(agents)
            cmd_str += f" --agents {safe_agents}"

        # Comandos base según plataforma
        if platform.system() == "Windows":
            return ["powershell", "-Command", cmd_str]
        else:  # Linux, macOS, Android, Termux, etc.
            return ["bash", "-c", cmd_str]
