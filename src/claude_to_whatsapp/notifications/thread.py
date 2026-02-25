"""Periodic notification thread."""

import time
import logging
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)


class NotificationThread:
    """Thread that sends periodic notifications for pending requests."""

    def __init__(self, interval: int = 30):
        """Initialize notification thread.

        Args:
            interval: Notification interval in seconds.
        """
        self.interval = interval
        self.running = False
        self.thread: threading.Thread | None = None
        self.lock = threading.Lock()
        self.pending_requests: Dict[str, Dict[str, Any]] = {}

    def add_request(self, chat_key: str, request_data: Dict[str, Any]) -> None:
        """Add a pending request.

        Args:
            chat_key: Unique identifier for the chat.
            request_data: Dictionary with request data (chat, client, start_time, prompt).
        """
        with self.lock:
            self.pending_requests[chat_key] = request_data

    def remove_request(self, chat_key: str) -> None:
        """Remove a pending request.

        Args:
            chat_key: Unique identifier for the chat.
        """
        with self.lock:
            self.pending_requests.pop(chat_key, None)

    def start(self) -> None:
        """Start the notification thread."""
        if self.running:
            return

        self.running = True

        def _loop():
            while self.running:
                try:
                    time.sleep(self.interval)
                    if not self.running:
                        break
                    self._send_notifications()
                except Exception as e:
                    logger.error(f"❌ Error en thread de notificaciones: {e}")

        self.thread = threading.Thread(target=_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop the notification thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _send_notifications(self) -> None:
        """Send notifications for pending requests."""
        current_time = time.time()

        with self.lock:
            expired_keys = []
            for chat_key, req_data in self.pending_requests.items():
                elapsed = int(current_time - req_data["start_time"])

                if elapsed >= self.interval:
                    minutes = elapsed // 60
                    seconds = elapsed % 60

                    if minutes > 0:
                        time_msg = f"BOTSYS:⏳ Tiempo transcurrido: {minutes}m {seconds}s"
                    else:
                        time_msg = f"BOTSYS:⏳ Tiempo transcurrido: {seconds}s"

                    try:
                        req_data["client"].send_message(req_data["chat"], time_msg)
                        logger.debug(f"📤 Notificación enviada a {chat_key}")
                    except Exception as e:
                        logger.error(f"❌ Error enviando notificación: {e}")
