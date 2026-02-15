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

    def ask(self, prompt: str, session_id: Optional[str] = None) -> Tuple[str, str]:
        """Ask Claude a prompt.

        Args:
            prompt: The prompt to send to Claude.
            session_id: Session ID to continue conversation. If None, creates new session.

        Returns:
            Tuple of (response, new_session_id).

        Raises:
            ClaudeTimeoutError: If Claude CLI times out.
            ClaudeConnectionError: If there's an error communicating with Claude.
        """
        cmd = self._build_command(prompt, session_id)

        try:
            logger.info(f"🤖 Enviando a Claude: {prompt[:50]}...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
            )
        except subprocess.TimeoutExpired:
            logger.error("⏱️ Timeout esperando respuesta de Claude")
            raise ClaudeTimeoutError(f"Timeout después de {self.timeout}s")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parseando JSON de Claude: {e}")
            raise ClaudeConnectionError(f"Invalid JSON response: {e}")

        response = json.loads(result.stdout)
        return response.get("result", ""), response.get("session_id", "")

    def _build_command(self, prompt: str, session_id: Optional[str]) -> list[str]:
        """Build Claude CLI command.

        Args:
            prompt: The prompt to send to Claude.
            session_id: Session ID for existing conversation.

        Returns:
            List of command arguments.
        """
        # Escapar el prompt de forma segura con shlex
        safe_prompt = shlex.quote(prompt)

        # Comandos base según plataforma
        if platform.system() == "Windows":
            cmd = ["powershell", "-Command",
                    f'claude --output-format json --permission-mode bypassPermissions -p {safe_prompt}']
        elif platform.system() == "Darwin":  # macOS
            cmd = ["bash", "-c",
                    f'claude --output-format json --permission-mode bypassPermissions -p {safe_prompt}']
        else:  # Linux, Android, Termux, etc.
            cmd = ["bash", "-c",
                    f'claude --output-format json --permission-mode bypassPermissions -p {safe_prompt}']

        if session_id:
            cmd.append(f"-r \"{session_id}\"")

        return cmd
