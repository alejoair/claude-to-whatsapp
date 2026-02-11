"""CLI entry point for claude-to-whatsapp."""

import sys
import os
from .config import Config
from .core.bot import WhatsAppBot
from .logging_config import configure_logging


def main():
    """Main entry point - runs the WhatsApp bot."""
    configure_logging()

    # Configurar directorio actual como directorio de trabajo
    work_dir = os.getcwd()

    print("=" * 50)
    print("claude-to-whatsapp v0.1.0")
    print("=" * 50)
    print(f"Directorio de trabajo: {work_dir}")
    print(f"Buscando .claude/ y system_prompt.txt en: {work_dir}")

    # Crear configuración
    config = Config(work_dir=work_dir)

    # Crear bot y ejecutar
    bot = WhatsAppBot(config)
    bot.run()


if __name__ == "__main__":
    main()
