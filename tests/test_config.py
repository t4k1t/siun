"""Test config module."""

import tomllib
from os import environ
from pathlib import Path
from unittest import mock

import pytest

from siun.config import get_config
from siun.errors import ConfigError
from siun.models import ClickColor

CONFIG_MISSING_WEIGHTS = """
[[v2_criteria]]
name = "custom"
"""

CONFIG_CUSTOM_STATE_FILE_PATH = """
state_file = "/tmp/siun-test-state.json"
"""

CONFIG_LEGACY_THRESHOLDS = """
cmd_available = "checkupdates --nocolor"
thresholds = { available = 1, warning = 2, critical = 3 }
[criteria]
count_weight = 1
"""

CONFIG_V2_THRESHOLDS = """
cmd_available = "checkupdates --nocolor"
[[v2_thresholds]]
name = "critical"
score = 3
color = "red"
text = "cr"

[[v2_thresholds]]
name = "warning"
score = 2
color = "yellow"
text = "wa"

[[v2_thresholds]]
name = "available"
score = 1
color = "green"
text = "av"

[criteria]
count_weight = 1
"""

CONFIG_W_DUPLICATE_T_NAMES = """
cmd_available = "checkupdates --nocolor"
[[v2_thresholds]]
name = "dupe"
score = 3
text = "cr"

[[v2_thresholds]]
name = "dupe"
score = 2
text = "wa"

[criteria]
count_weight = 1
"""

CONFIG_W_INVALID_NOTIFICATION_THRESHOLD = """
cmd_available = "checkupdates --nocolor"
thresholds = { available = 1, warning = 2, critical = 3 }
[criteria]
count_weight = 1
[notification]
threshold = "non-existent-threshold"
"""

# Override `$HOME` for consistent tests
environ["HOME"] = "/tmp/siun-tests"  # noqa: S108


def mock_read_config(_):
    """Mock empty config file."""
    return tomllib.loads("")


class TestConfig:
    """Test Config class."""

    @mock.patch("siun.config._read_config", mock_read_config)
    def test_default_config(self, default_config):
        """Test empty user config."""
        with (
            mock.patch("pathlib.Path.exists", return_value=True),
            mock.patch("pathlib.Path.is_file", return_value=True),
        ):
            config = get_config()

        assert config == default_config
        assert config.cmd_available == "pacman -Quq; if [ $? == 1 ]; then :; fi"

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_MISSING_WEIGHTS))
    def test_missing_weights(self, mock_read_config):
        """Test user config with missing weights."""
        with mock.patch("siun.config.get_default_config_dir"), pytest.raises(ConfigError) as exc_info:
            get_config()

        mock_read_config.assert_called_once()
        assert "'v2_criteria.0.weight': Field required" in str(exc_info.value)

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_CUSTOM_STATE_FILE_PATH))
    def test_custom_state_file_path(self, mock_read_config, default_config):
        """Test custom state file path."""
        with mock.patch("siun.config.get_default_config_dir"):
            config = get_config()
        assert config != default_config
        assert config.state_file == Path("/tmp/siun-test-state.json")  # noqa: S108

        mock_read_config.assert_called_once()

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_W_INVALID_NOTIFICATION_THRESHOLD))
    def test_invalid_notification_threshold(self, mock_read_config, default_config):
        """Test notification.threshold validation."""
        with mock.patch("siun.config.get_default_config_dir"), pytest.raises(ConfigError) as exc_info:  # noqa: PT011
            get_config()

        mock_read_config.assert_called_once()
        assert "notification.threshold must be one of" in str(exc_info.value)

    @mock.patch("siun.config._read_config", mock_read_config)
    def test_xdg_state_home_set(self, default_config):
        """Test XDG_STATE_HOME being set."""
        with mock.patch.dict(environ, clear=True):
            environ["XDG_STATE_HOME"] = "/tmp/siun-tests/state"  # noqa: S108
            config = get_config()

        assert config.state_file == Path("/tmp/siun-tests/state/siun/state.json")  # noqa: S108

    @mock.patch("siun.config._read_config", side_effect=OSError)
    def test_os_error(self, default_config):
        """Test handling of OSError."""
        with mock.patch("siun.config.get_default_config_dir"), pytest.raises(ConfigError) as exc_info:  # noqa: PT011
            get_config()

        assert "failed to open config file" in str(exc_info.value)

    @mock.patch("siun.config._read_config", side_effect=tomllib.TOMLDecodeError)
    def test_toml_error(self, default_config):
        """Test handling of TOMLDecodeError."""
        with mock.patch("siun.config.get_default_config_dir"), pytest.raises(ConfigError) as exc_info:  # noqa: PT011
            get_config()

        assert "config file not valid" in str(exc_info.value)


class TestThresholdsConfig:
    """Test config with legacy and v2 thresholds."""

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_LEGACY_THRESHOLDS))
    def test_legacy_thresholds(self, mock_read_config):
        """Test config using legacy 'thresholds' dict."""
        with mock.patch("siun.config.get_default_config_dir"):
            config = get_config()

        names = [t.name for t in config.v2_thresholds]
        scores = [t.score for t in config.v2_thresholds]

        assert set(names) == {"critical", "warning", "available"}
        assert set(scores) == {1, 2, 3}
        mock_read_config.assert_called_once()

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_V2_THRESHOLDS))
    def test_v2_thresholds(self, mock_read_config):
        """Test config using v2_thresholds list."""
        with mock.patch("siun.config.get_default_config_dir"):
            config = get_config()

        names = [t.name for t in config.v2_thresholds]
        scores = [t.score for t in config.v2_thresholds]
        colors = [getattr(t, "color", None) for t in config.v2_thresholds]

        assert set(names) == {"critical", "warning", "available"}
        assert set(scores) == {1, 2, 3}
        assert set(colors) == {ClickColor.red, ClickColor.yellow, ClickColor.green}
        mock_read_config.assert_called_once()

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_LEGACY_THRESHOLDS))
    def test_thresholds_equivalence(self, mock_read_config):
        """Test that legacy and v2 thresholds produce equivalent sorted_thresholds."""
        with mock.patch("siun.config.get_default_config_dir"):
            config_legacy = get_config()
        sorted_legacy = [(t.name, t.score) for t in config_legacy.sorted_thresholds]

        with (
            mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_V2_THRESHOLDS)),
            mock.patch("pathlib.Path.exists", return_value=True),
            mock.patch("pathlib.Path.is_file", return_value=True),
        ):
            config_v2 = get_config()
        sorted_v2 = [(t.name, t.score) for t in config_v2.sorted_thresholds]

        assert sorted_legacy == sorted_v2

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_W_DUPLICATE_T_NAMES))
    def test_v2_thresholds_name_uniqueness(self, mock_read_config):
        """Test v2_thresholds require unique names."""
        with mock.patch("siun.config.get_default_config_dir"), pytest.raises(ConfigError) as exc_info:
            get_config()

        mock_read_config.assert_called_once()
        assert "threshold must have a unique name" in str(exc_info.value)
