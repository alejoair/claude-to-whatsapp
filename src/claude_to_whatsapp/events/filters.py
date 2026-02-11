"""Message filters for WhatsApp messages."""

from typing import Optional


class MessageFilter:
    """Filters for WhatsApp messages."""

    @staticmethod
    def is_self_message(msg_source) -> bool:
        """Check if message is a self-message.

        A self-message must satisfy both:
        - IsFromMe == True
        - sender == chat

        Args:
            msg_source: Message source object from Neonize.

        Returns:
            True if message is a self-message.
        """
        is_from_me = msg_source.IsFromMe
        sender_str = str(msg_source.Sender.User)
        chat_str = str(msg_source.Chat.User)

        return is_from_me and (sender_str == chat_str)

    @staticmethod
    def is_system_message(text: str, prefix: str = "BOTSYS:") -> bool:
        """Check if message is a system message.

        Args:
            text: Message text.
            prefix: System message prefix.

        Returns:
            True if message is a system message.
        """
        return text.startswith(prefix)

    @staticmethod
    def is_bot_command(text: str, prefix: str = "BOTSET:") -> bool:
        """Check if message is a bot command.

        Args:
            text: Message text.
            prefix: Bot command prefix.

        Returns:
            True if message is a bot command.
        """
        return text.startswith(prefix)

    @staticmethod
    def extract_text(message) -> Optional[str]:
        """Extract text from WhatsApp message.

        Args:
            message: WhatsApp message object.

        Returns:
            Message text or None if not found.
        """
        msg = message.Message

        if hasattr(msg, "conversation") and msg.conversation:
            return str(msg.conversation)
        elif hasattr(msg, "extendedTextMessage") and msg.extendedTextMessage:
            if hasattr(msg.extendedTextMessage, "text"):
                return str(msg.extendedTextMessage.text)
        elif hasattr(msg, "protocolMessage"):
            return None

        return None
