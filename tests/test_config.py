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

CONFIG_CUSTOM_STATE_DIR = """
state_dir = "/tmp/siun-test-state"
"""

CONFIG_LEGACY_THRESHOLDS = """
thresholds = { available = 1, warning = 2, critical = 3 }
[[update_providers]]
name = "pacman"
[[v2_criteria]]
name = "count"
weight = 1
count = 15
"""

CONFIG_LEGACY_CRITERIA = """
[[update_providers]]
name = "pacman"
[criteria]
critical_pattern = "^package$"
critical_weight = 1
count_threshold = 30
count_weight = 1
"""

CONFIG_V2_THRESHOLDS = """
[[update_providers]]
name = "pacman"
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

[[v2_criteria]]
name = "count"
weight = 1
count = 15
"""

CONFIG_W_DUPLICATE_T_NAMES = """
[[update_providers]]
name = "pacman"
[[v2_thresholds]]
name = "dupe"
score = 3
text = "cr"

[[v2_thresholds]]
name = "dupe"
score = 2
text = "wa"

[[v2_criteria]]
name = "count"
weight = 1
count = 15
"""

CONFIG_W_INVALID_NOTIFICATION_THRESHOLD = """
[[update_providers]]
name = "pacman"
[[v2_criteria]]
name = "count"
weight = 1
count = 15
[notification]
threshold = "non-existent-threshold"
"""

CONFIG_W_NEWS = """
[[news]]
url = "https://pypi.org/rss/project/siun/releases.xml"
title = "Test Title"
max_items = 1
"""

# Override `$HOME` for consistent tests
environ["HOME"] = "/tmp/siun-tests"  # noqa: S108


def mock_read_config(_):
    """Mock empty config file."""
    return tomllib.loads("")


@pytest.mark.usefixtures("patch_is_path_world_writable")
class TestConfig:
    """Test Config class."""

    @mock.patch("siun.config._read_config", mock_read_config)
    def test_default_config(self, default_config, default_update_providers):
        """Test empty user config."""
        with (
            mock.patch("pathlib.Path.exists", return_value=True),
            mock.patch("pathlib.Path.is_file", return_value=True),
        ):
            config = get_config()

        assert config == default_config
        assert config.update_providers == default_update_providers

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_MISSING_WEIGHTS))
    def test_missing_weights(self, mock_read_config):
        """Test user config with missing weights."""
        with mock.patch("siun.config.get_default_config_dir"), pytest.raises(ConfigError) as exc_info:
            get_config()

        mock_read_config.assert_called_once()
        assert "'v2_criteria.0.weight': Field required" in str(exc_info.value)

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_CUSTOM_STATE_DIR))
    def test_custom_state_dir(self, mock_read_config, default_config):
        """Test custom state file path."""
        with mock.patch("siun.config.get_default_config_dir"):
            config = get_config()
        assert config != default_config
        assert config.state_dir == Path("/tmp/siun-test-state")  # noqa: S108

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
        with (
            mock.patch.dict(environ, clear=True),
            mock.patch("pathlib.Path.exists", return_value=True),
            mock.patch("pathlib.Path.is_file", return_value=True),
        ):
            environ["XDG_STATE_HOME"] = "/tmp/siun-tests/state"  # noqa: S108
            config = get_config()

        assert config.state_dir == Path("/tmp/siun-tests/state/siun")  # noqa: S108

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

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_W_NEWS))
    def test_config_with_news_source(self, default_config):
        """Test config with news source."""
        with (
            mock.patch("pathlib.Path.exists", return_value=True),
            mock.patch("pathlib.Path.is_file", return_value=True),
        ):
            config = get_config()

        assert len(config.news) == 1
        news_source = config.news[0]
        assert news_source.url == "https://pypi.org/rss/project/siun/releases.xml"
        assert news_source.title == "Test Title"
        assert news_source.max_items == 1


@pytest.mark.usefixtures("patch_is_path_world_writable")
class TestThresholdsConfig:
    """Test config with v2 thresholds."""

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_LEGACY_THRESHOLDS))
    def test_legacy_thresholds_raises_error(self, mock_read_config):
        """Test config using legacy 'thresholds' dict."""
        with mock.patch("siun.config.get_default_config_dir"), pytest.raises(ConfigError) as exc_info:
            get_config()

        mock_read_config.assert_called_once()
        assert "deprecated config fields: \n- 'thresholds'" in str(exc_info.value)

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_V2_THRESHOLDS))
    def test_v2_thresholds(self, mock_read_config):
        """Test config using v2_thresholds list."""
        with (
            mock.patch("siun.config.get_default_config_dir"),
        ):
            config = get_config()

        names = [t.name for t in config.v2_thresholds]
        scores = [t.score for t in config.v2_thresholds]
        colors = [getattr(t, "color", None) for t in config.v2_thresholds]

        assert set(names) == {"critical", "warning", "available"}
        assert set(scores) == {1, 2, 3}
        assert set(colors) == {ClickColor.red, ClickColor.yellow, ClickColor.green}
        mock_read_config.assert_called_once()

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_W_DUPLICATE_T_NAMES))
    def test_v2_thresholds_name_uniqueness(self, mock_read_config):
        """Test v2_thresholds require unique names."""
        with (
            mock.patch("siun.config.get_default_config_dir"),
            pytest.raises(ConfigError) as exc_info,
        ):
            get_config()

        mock_read_config.assert_called_once()
        assert "threshold must have a unique name" in str(exc_info.value)


@pytest.mark.usefixtures("patch_is_path_world_writable")
class TestCriteriaConfig:
    """Test config with v2 criteria."""

    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_LEGACY_CRITERIA))
    def test_legacy_criteria_raises_error(self, mock_read_config):
        """Test config using legacy 'criteria' dict."""
        with (
            mock.patch("siun.config.get_default_config_dir"),
            pytest.raises(ConfigError) as exc_info,
        ):
            get_config()

        mock_read_config.assert_called_once()
        assert "deprecated config fields: \n- 'criteria'" in str(exc_info.value)
