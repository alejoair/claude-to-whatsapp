"""claude-to-whatsapp: WhatsApp bot con integración a Claude AI CLI.

El bot se ejecuta en un directorio que contiene:
- system_prompt.txt: System prompt personalizado para Claude
- .claude/agents/: Directorio con definiciones de agentes (.md)
- .claude/skills/: Directorio con definiciones de skills

Cuando Claude CLI se ejecuta, lee estos archivos del directorio actual.
"""

from claude_to_whatsapp.core.bot import WhatsAppBot
from claude_to_whatsapp.config import Config

__version__ = "0.1.0"
__all__ = ["WhatsAppBot", "Config", "__version__"]
