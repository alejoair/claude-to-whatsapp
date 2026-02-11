"""Logging configuration for claude-to-whatsapp."""

import logging
import os


def configure_logging(level: str = "INFO") -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    home = os.path.expanduser("~")
    log_dir = os.path.join(home, ".claude-to-whatsapp")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "whatsapp.log")

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
