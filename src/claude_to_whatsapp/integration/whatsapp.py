"""WhatsApp client wrapper using Neonize."""

import logging
import time
import threading
from typing import Callable
from neonize.client import NewClient
from neonize.events import ConnectedEv, PairStatusEv, MessageEv, HistorySyncEv, DisconnectedEv, StreamErrorEv
from .base import MessageClient

logger = logging.getLogger(__name__)


class WhatsAppClient(MessageClient):
    """WhatsApp client wrapper con reconexión automática."""

    def __init__(self, db_path: str):
        """Initialize WhatsApp client.

        Args:
            db_path: Path to WhatsApp session database.
        """
        self.db_path = db_path
        self._client: NewClient | None = None
        self._handlers: dict = {}
        self._reconnect_lock = threading.Lock()
        self._auto_reconnect = True  # Habilitar reconexión automática
        self._is_connecting = False
        self._should_run = True  # Flag para controlar el loop de reconexión

    def connect(self) -> None:
        """Connect to WhatsApp."""
        with self._reconnect_lock:
            if self._is_connecting:
                return
            self._is_connecting = True

        try:
            self._client = NewClient(self.db_path)

            # Registrar handlers pendientes después de crear el cliente
            self._register_pending_handlers()
            # Registrar handler de desconexión
            self._client.event(DisconnectedEv)(self._on_disconnected)
            self._client.event(StreamErrorEv)(self._on_stream_error)

            self._client.connect()

        except Exception as e:
            logger.error(f"[WhatsAppClient.connect] ❌ Error conectando: {e}", exc_info=True)
            self._client = None
        finally:
            self._is_connecting = False

    def _on_disconnected(self, client: NewClient, event: DisconnectedEv) -> None:
        """Manejar evento de desconexión."""
        logger.warning("[WhatsAppClient] Desconectado de WhatsApp")
        if self._auto_reconnect:
            time.sleep(5)  # Esperar antes de reconectar
            if self._should_run:
                self.connect()

    def _on_stream_error(self, client: NewClient, event: StreamErrorEv) -> None:
        """Manejar errores de stream."""
        logger.warning(f"[WhatsAppClient] Error de stream")
        if self._auto_reconnect:
            time.sleep(3)
            if self._should_run:
                self.connect()

    def _register_pending_handlers(self) -> None:
        """Registra todos los handlers pendientes en el cliente."""
        for event_type, handler_list in self._handlers.items():
            for handler in handler_list:
                self._client.event(event_type)(handler)

    def disconnect(self) -> None:
        """Disconnect from WhatsApp."""
        self._should_run = False
        self._auto_reconnect = False
        if self._client:
            self._client.disconnect()

    def send_message(self, recipient, message: str) -> None:
        """Send a message to a recipient."""
        if self._client:
            self._client.send_message(recipient, message)

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._client is not None

    def download_media(self, message, path: str) -> None:
        """Download media from message to path.

        Args:
            message: WhatsApp message with media.
            path: Path to save the media.
        """
        if not self._client:
            return

        # Extraer datos de imagen del mensaje
        msg = message.Message
        if hasattr(msg, "imageMessage") and msg.imageMessage:
            img = msg.imageMessage
            from neonize.utils.enum import MediaType, MediaTypeToMMS

            # Crear MediaType y MMS type
            media_type = MediaType.MediaImage
            mms_type = MediaTypeToMMS.MediaImage

            data = self._client.download_media_with_path(
                direct_path=img.directPath,
                enc_file_hash=img.fileEncSHA256,
                file_hash=img.fileSHA256,
                media_key=img.mediaKey,
                file_length=img.fileLength,
                media_type=media_type,
                mms_type=mms_type
            )

            # Guardar archivo
            with open(path, "wb") as f:
                f.write(data)
        else:
            # Fallback a download_any para otros tipos de media
            self._client.download_any(message, path)

    def register_handler(self, event_type, handler: Callable) -> None:
        """Register an event handler.

        Args:
            event_type: Neonize event type (ConnectedEv, MessageEv, etc.).
            handler: Handler function.
        """
        if self._client:
            self._client.event(event_type)(handler)
        else:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
