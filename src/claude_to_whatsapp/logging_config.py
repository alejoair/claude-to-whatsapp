"""Logging configuration for claude-to-whatsapp."""

import logging
import os


def configure_logging(level: str = "WARNING") -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Default is WARNING to reduce verbosity.
    """
    home = os.path.expanduser("~")
    log_dir = os.path.join(home, ".claude-to-whatsapp")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "bot.log")

    # Configurar logging base
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s.%(msecs)03d [%(name)s %(levelname)s] - %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )

    # Silenciar librerías externas
    logging.getLogger("whatsmeow").setLevel(logging.ERROR)
    logging.getLogger("neonize").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)


