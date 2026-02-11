"""Data models for claude-to-whatsapp."""

from dataclasses import dataclass


@dataclass
class ClaudeRequest:
    """Request to Claude AI."""

    prompt: str
    session_id: str | None = None


@dataclass
class ClaudeResponse:
    """Response from Claude AI."""

    result: str
    session_id: str
