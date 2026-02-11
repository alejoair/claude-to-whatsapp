"""Custom exceptions for claude-to-whatsapp."""


class ClaudeToWhatsAppError(Exception):
    """Base exception for claude-to-whatsapp."""

    pass


class ClaudeTimeoutError(ClaudeToWhatsAppError):
    """Raised when Claude CLI times out."""

    pass


class ClaudeConnectionError(ClaudeToWhatsAppError):
    """Raised when there's an error connecting to Claude."""

    pass


class WhatsAppConnectionError(ClaudeToWhatsAppError):
    """Raised when there's an error connecting to WhatsApp."""

    pass
