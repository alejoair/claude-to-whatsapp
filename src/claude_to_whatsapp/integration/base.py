"""Base interfaces for integrations."""

from abc import ABC, abstractmethod


class MessageClient(ABC):
    """Base interface for message clients."""

    @abstractmethod
    def connect(self) -> None:
        """Connect to message service."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from message service."""
        pass

    @abstractmethod
    def send_message(self, recipient, message: str) -> None:
        """Send a message to a recipient."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        pass


class AIModelClient(ABC):
    """Base interface for AI model clients."""

    @abstractmethod
    def ask(self, prompt: str, session_id: str | None = None) -> tuple[str, str]:
        """Ask AI model a prompt.

        Returns:
            Tuple of (response, new_session_id).
        """
        pass
