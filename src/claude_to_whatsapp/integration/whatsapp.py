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
                logger.info("[WhatsAppClient.connect] Ya hay una conexión en progreso, esperando...")
                return
            self._is_connecting = True

        try:
            logger.info(f"[WhatsAppClient.connect] Creando NewClient con db_path={self.db_path}")
            self._client = NewClient(self.db_path)
            logger.info(f"[WhatsAppClient.connect] Cliente creado: {self._client}")

            # Registrar handlers pendientes después de crear el cliente
            self._register_pending_handlers()
            # Registrar handler de desconexión
            self._client.event(DisconnectedEv)(self._on_disconnected)
            self._client.event(StreamErrorEv)(self._on_stream_error)

            logger.info(f"[WhatsAppClient.connect] Llamando a client.connect()")
            self._client.connect()
            logger.info(f"[WhatsAppClient.connect] client.connect() completado")

        except Exception as e:
            logger.error(f"[WhatsAppClient.connect] ❌ Error conectando: {e}", exc_info=True)
            # Si falla la conexión inicial y está habilitada la reconexión,
            # el loop de reconexión lo manejará
            self._client = None
        finally:
            self._is_connecting = False

    def _on_disconnected(self, client: NewClient, event: DisconnectedEv) -> None:
        """Manejar evento de desconexión."""
        logger.warning("[WhatsAppClient._on_disconnected] ⚠️ Desconectado de WhatsApp")
        if self._auto_reconnect:
            logger.info("[WhatsAppClient._on_disconnected] Reconexión automática habilitada, reintentando en 5 segundos...")
            time.sleep(5)  # Esperar antes de reconectar
            if self._should_run:
                self.connect()

    def _on_stream_error(self, client: NewClient, event: StreamErrorEv) -> None:
        """Manejar errores de stream."""
        logger.warning(f"[WhatsAppClient._on_stream_error] ⚠️ Error de stream: {event}")
        if self._auto_reconnect:
            logger.info("[WhatsAppClient._on_stream_error] Reconectando en 3 segundos...")
            time.sleep(3)
            if self._should_run:
                self.connect()

    def _register_pending_handlers(self) -> None:
        """Registra todos los handlers pendientes en el cliente."""
        logger.info(f"[WhatsAppClient._register_pending_handlers] Handlers pendientes: {list(self._handlers.keys())}")
        for event_type, handler_list in self._handlers.items():
            logger.info(f"[WhatsAppClient._register_pending_handlers] Evento: {event_type.__name__}, Handlers: {len(handler_list)}")
            for idx, handler in enumerate(handler_list):
                logger.info(f"[WhatsAppClient._register_pending_handlers] Registrando handler #{idx} para {event_type.__name__}: {handler}")
                try:
                    self._client.event(event_type)(handler)
                    logger.info(f"[WhatsAppClient._register_pending_handlers] ✅ Handler #{idx} registrado correctamente para {event_type.__name__}")
                except Exception as e:
                    logger.error(f"[WhatsAppClient._register_pending_handlers] ❌ Error registrando handler #{idx} para {event_type.__name__}: {e}", exc_info=True)

    def disconnect(self) -> None:
        """Disconnect from WhatsApp."""
        logger.info(f"[WhatsAppClient.disconnect] Desconectando...")
        self._should_run = False  # Detener reconexión automática
        self._auto_reconnect = False  # Deshabilitar reconexión
        if self._client:
            try:
                self._client.disconnect()
            except Exception as e:
                logger.error(f"[WhatsAppClient.disconnect] ❌ Error desconectando: {e}", exc_info=True)
        logger.info(f"[WhatsAppClient.disconnect] Desconectado")

    def send_message(self, recipient, message: str) -> None:
        """Send a message to a recipient."""
        logger.debug(f"[WhatsAppClient.send_message] Enviando mensaje a {recipient}")
        if self._client:
            try:
                self._client.send_message(recipient, message)
                logger.info(f"[WhatsAppClient.send_message] ✅ Mensaje enviado")
            except Exception as e:
                logger.error(f"[WhatsAppClient.send_message] ❌ Error enviando mensaje: {e}", exc_info=True)
        else:
            logger.error(f"[WhatsAppClient.send_message] ❌ Cliente es None, no se puede enviar mensaje")

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._client is not None

    def register_handler(self, event_type, handler: Callable) -> None:
        """Register an event handler.

        Args:
            event_type: Neonize event type (ConnectedEv, MessageEv, etc.).
            handler: Handler function.
        """
        logger.info(f"[WhatsAppClient.register_handler] Registrando handler para {event_type.__name__}: {handler}")
        logger.info(f"[WhatsAppClient.register_handler] self._client existe: {self._client is not None}")

        if self._client:
            logger.info(f"[WhatsAppClient.register_handler] Registrando directamente en cliente existente")
            try:
                self._client.event(event_type)(handler)
                logger.info(f"[WhatsAppClient.register_handler] ✅ Handler registrado directamente para {event_type.__name__}")
            except Exception as e:
                logger.error(f"[WhatsAppClient.register_handler] ❌ Error registrando handler directamente: {e}", exc_info=True)
        else:
            # Guardar handler para cuando el cliente se cree
            logger.info(f"[WhatsAppClient.register_handler] Guardando handler para registro posterior")
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            logger.info(f"[WhatsAppClient.register_handler] ✅ Handler guardado. Total handlers para {event_type.__name__}: {len(self._handlers[event_type])}")
