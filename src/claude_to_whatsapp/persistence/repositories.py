"""Repositories for data persistence."""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BotConfigRepository:
    """Repository for bot configuration stored in SQLite."""

    def __init__(self, db_path: str):
        """Initialize repository.

        Args:
            db_path: Path to SQLite database.
        """
        self.db_path = Path(db_path).expanduser()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS bot_config (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """
                )
                conn.commit()
            logger.info(f"✅ DB inicializada: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Error inicializando DB: {e}")

    def get(self, key: str) -> Optional[str]:
        """Get a configuration value.

        Args:
            key: Configuration key.

        Returns:
            Configuration value or None if not found.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT value FROM bot_config WHERE key = ?", (key,)
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"❌ Error obteniendo {key}: {e}")
            return None

    def set(self, key: str, value: str) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key.
            value: Configuration value.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO bot_config (key, value) VALUES (?, ?)",
                    (key, value),
                )
                conn.commit()
            logger.debug(f"💾 {key} guardado: {value[:30]}...")
        except Exception as e:
            logger.error(f"❌ Error guardando {key}: {e}")

    def delete(self, key: str) -> None:
        """Delete a configuration value.

        Args:
            key: Configuration key.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM bot_config WHERE key = ?", (key,))
                conn.commit()
            logger.debug(f"🗑️ {key} eliminado")
        except Exception as e:
            logger.error(f"❌ Error eliminando {key}: {e}")
