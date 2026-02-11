"""Tests for config module."""

from claude_to_whatsapp.config import Config, ClaudeConfig, WhatsAppConfig


def test_config_creation(tmp_path):
    """Test that Config can be created."""
    config = Config(work_dir=str(tmp_path))
    assert config.work_dir == str(tmp_path)
    assert config.claude is not None
    assert config.whatsapp is not None
    assert config.bot is not None


def test_config_properties(tmp_path):
    """Test that config properties return correct paths."""
    config = Config(work_dir=str(tmp_path))
    assert tmp_path in config.agents_dir
    assert tmp_path in config.skills_dir
    assert tmp_path in config.system_prompt_path
