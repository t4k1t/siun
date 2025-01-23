"""Test config module."""

import tomllib
from os import environ
from pathlib import Path
from unittest import mock

import pytest
from pydantic import ValidationError

from siun.config import get_config

CONFIG_MISSING_WEIGHTS = """
[criteria]
custom_threshold = 1000
"""

CONFIG_CUSTOM_STATE_FILE_PATH = """
state_file = "/tmp/siun-test-state.json"
"""

# Override `$HOME` for consistent tests
environ["HOME"] = "/tmp/siun-tests"  # noqa: S108


def mock_read_config(_):
    """Mock empty config file."""
    return tomllib.loads("")


class TestConfig:
    """Test Updates class."""

    @mock.patch("siun.config._read_config", mock_read_config)
    def test_default_config(self, default_config):
        """Test empty user config."""
        config = get_config()

        assert config == default_config
        assert config.cmd_available == "pacman -Quq"

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_MISSING_WEIGHTS))
    def test_missing_weights(self, mock_read_config):
        """Test user config with missing weights."""
        with mock.patch("siun.config.CONFIG_PATH"), pytest.raises(ValidationError) as exc_info:
            get_config()

        mock_read_config.assert_called_once()
        assert "missing weight" in str(exc_info.value)

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_CUSTOM_STATE_FILE_PATH))
    def test_custom_state_file_path(self, mock_read_config, default_config):
        """Test user config with missing weights."""
        with mock.patch("siun.config.CONFIG_PATH"):
            config = get_config()
        assert config != default_config
        assert config.state_file == Path("/tmp/siun-test-state.json")  # noqa: S108

        mock_read_config.assert_called_once()

    @mock.patch("siun.config._read_config", mock_read_config)
    def test_xdg_state_home_set(self, default_config):
        """Test XDG_STATE_HOME being set."""
        with mock.patch.dict(environ, clear=True):
            environ["XDG_STATE_HOME"] = "/tmp/siun-tests/state"  # noqa: S108
            config = get_config()

        assert config.state_file == Path("/tmp/siun-tests/state/siun/state.json")  # noqa: S108
