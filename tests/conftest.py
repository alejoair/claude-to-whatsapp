"""Pytest fixtures for claude-to-whatsapp tests."""

import pytest


@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary config for testing."""
    from claude_to_whatsapp.config import Config

    config = Config(work_dir=str(tmp_path))
    return config
