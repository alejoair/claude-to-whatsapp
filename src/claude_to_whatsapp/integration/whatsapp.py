"""WhatsApp client wrapper using Neonize."""

from typing import Callable
from neonize.client import NewClient
from neonize.events import ConnectedEv, PairStatusEv, MessageEv, HistorySyncEv
from .base import MessageClient


class WhatsAppClient(MessageClient):
    """WhatsApp client wrapper."""

    def __init__(self, db_path: str):
        """Initialize WhatsApp client.

        Args:
            db_path: Path to WhatsApp session database.
        """
        self.db_path = db_path
        self._client: NewClient | None = None
        self._handlers: dict = {}

    def connect(self) -> None:
        """Connect to WhatsApp."""
        self._client = NewClient(self.db_path)

        # Registrar handlers pendientes después de crear el cliente
        self._register_pending_handlers()

        self._client.connect()

    def _register_pending_handlers(self) -> None:
        """Registra todos los handlers pendientes en el cliente."""
        for event_type, handler_list in self._handlers.items():
            for handler in handler_list:
                self._client.event(event_type)(handler)

    def disconnect(self) -> None:
        """Disconnect from WhatsApp."""
        if self._client:
            self._client.disconnect()

    def send_message(self, recipient, message: str) -> None:
        """Send a message to a recipient."""
        if self._client:
            self._client.send_message(recipient, message)

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._client is not None

    def register_handler(self, event_type, handler: Callable) -> None:
        """Register an event handler.

        Args:
            event_type: Neonize event type (ConnectedEv, MessageEv, etc.).
            handler: Handler function.
        """
        if self._client:
            self._client.event(event_type)(handler)
        else:
            # Guardar handler para cuando el cliente se cree
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
