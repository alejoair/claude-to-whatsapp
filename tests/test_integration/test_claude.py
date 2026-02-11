"""Tests for ClaudeClient."""

import pytest
from claude_to_whatsapp.integration.claude import ClaudeClient
from claude_to_whatsapp.exceptions import ClaudeTimeoutError


def test_claude_client_creation():
    """Test that ClaudeClient can be created."""
    client = ClaudeClient(timeout=300)
    assert client.timeout == 300
    assert client.skip_permissions is True


def test_build_command_without_session_id():
    """Test command building without session_id."""
    client = ClaudeClient()
    cmd = client._build_command("test prompt", None)
    assert len(cmd) == 2  # ["powershell", "-Command <script>"]


def test_build_command_with_session_id():
    """Test command building with session_id."""
    client = ClaudeClient()
    cmd = client._build_command("test prompt", "session-123")
    assert len(cmd) == 2
