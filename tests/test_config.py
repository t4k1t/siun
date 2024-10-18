from unittest import mock

import pytest
import tomllib
from pydantic import ValidationError

from siun.config import get_config

CONFIG_MISSING_WEIGHTS = """
[criteria]
custom_threshold = 1000
"""


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

    @mock.patch("siun.config._read_config")
    def test_missing_weights(self, mock_read_config):
        """Test empty user config."""
        mock_read_config.return_value = tomllib.loads(CONFIG_MISSING_WEIGHTS)
        with pytest.raises(ValidationError) as exc_info:
            get_config()
        assert "missing weight" in str(exc_info.value)
