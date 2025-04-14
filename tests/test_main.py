"""Test main function and CLI."""

import datetime
import subprocess
import tomllib
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from siun.errors import CmdRunError, ConfigError
from siun.main import _get_available_updates, _get_updates, check
from siun.state import SiunState, State

EMPTY_STATE = SiunState(
    criteria_settings={},
    thresholds={},
    available_updates=[],
    matched_criteria={},
    state=State.OK,
    last_update=datetime.datetime.now(tz=datetime.UTC),
)

STALE_STATE = SiunState(
    criteria_settings={
        "available_weight": 1,
        "critical_weight": 0,
        "count_weight": 0,
        "lastupdate_weight": 0,
    },
    thresholds={},
    available_updates=[],
    matched_criteria={"available": {"weight": 1}},
    state=State.AVAILABLE_UPDATES,
    last_update=datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1),
)

WARNING_STATE = SiunState(
    criteria_settings={
        "available_weight": 1,
        "critical_weight": 0,
        "count_weight": 0,
        "lastupdate_weight": 0,
    },
    thresholds={},
    available_updates=[],
    matched_criteria={"available": {"weight": 1}, "count": {"weight": 1}},
    state=State.WARNING_UPDATES,
    last_update=datetime.datetime.now(tz=datetime.UTC),
    last_state=State.AVAILABLE_UPDATES,
)

AVAILABLE_STATE = SiunState(
    criteria_settings={
        "available_weight": 1,
        "critical_weight": 1,
        "count_weight": 1,
        "lastupdate_weight": 0,
    },
    thresholds={},
    available_updates=[],
    matched_criteria={"available": {"weight": 1}},
    state=State.AVAILABLE_UPDATES,
    last_update=datetime.datetime.now(tz=datetime.UTC),
    last_state=State.WARNING_UPDATES,
)

CONFIG_CUSTOM_STATE_FILE_PATH = """
state_file = "/tmp/siun-test-state.json"
"""


class TestMain:
    """Test main function."""

    @mock.patch("siun.main.Updates.persist_state")
    @mock.patch("siun.main.Updates.read_state")
    @mock.patch("siun.main._get_available_updates", return_value=[])
    @mock.patch("siun.main.get_config")
    def test_check_no_available_updates_no_cache(
        self, mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test check CLI command with no updates and --no-cache option."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check, ["-n"])
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        mock_get_available_updates.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "Ok\n"

    @mock.patch("siun.main.Updates.persist_state")
    @mock.patch("siun.main.Updates.read_state")
    @mock.patch("siun.main._get_available_updates", return_value=[])
    @mock.patch("siun.main.get_config")
    def test_check_no_cache_no_update_options(
        self, mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test check CLI command with --no-cache and --no-update options."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check, ["-n", "--no-update"])
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        mock_get_available_updates.assert_not_called()
        assert result.exit_code == 1
        assert result.output == "Error: --no-update and --no-cache options are mutually exclusive\n"

    @mock.patch("siun.main.Updates.persist_state")
    @mock.patch("siun.main.Updates.read_state")
    @mock.patch("siun.main._get_available_updates", return_value=[])
    @mock.patch("siun.main.get_config")
    def test_check_quiet_option(
        self, mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test check CLI command with no updates and --quiet option."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check, ["-n", "-q"])
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        mock_get_available_updates.assert_called_once()
        assert result.exit_code == 0
        assert result.output == ""

    @mock.patch("siun.main.Updates.persist_state")
    @mock.patch("siun.main.Updates.read_state", return_value=EMPTY_STATE)
    @mock.patch("siun.main._get_available_updates", return_value=[])
    @mock.patch("siun.main.get_config")
    def test_check_no_updates(
        self, mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test check CLI command with no updates."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check)
        mock_read_state.assert_called_once()
        mock_persist_state.assert_not_called()
        mock_get_available_updates.assert_not_called()
        assert result.exit_code == 0
        assert result.output == "Ok\n"

    @mock.patch("siun.main.Updates.persist_state")
    @mock.patch("siun.main.Updates.read_state")
    @mock.patch("siun.main._get_available_updates")
    @mock.patch("siun.main.get_config", side_effect=ConfigError("failed", config_path=Path("/path/to/siun.toml")))
    def test_check_invalid_config(
        self, mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test get_state CLI command with invalid config."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check)
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        mock_get_available_updates.assert_not_called()
        assert result.exit_code == 1
        assert result.output == "Error: failed; config path: /path/to/siun.toml\n"

    @mock.patch("siun.main.Updates.persist_state")
    @mock.patch("siun.main.Updates.read_state", return_value=STALE_STATE)
    @mock.patch("siun.main._get_available_updates", return_value=["package"])
    @mock.patch("siun.main.get_config")
    def test_check_stale_state(
        self, mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test check CLI command with stale state on disk."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check)
        mock_read_state.assert_called_once()
        mock_persist_state.assert_called_once()
        mock_get_available_updates.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "Updates available\n"

    @mock.patch("siun.main.Updates.persist_state")
    @mock.patch("siun.main.Updates.read_state", return_value=STALE_STATE)
    @mock.patch("siun.main._get_available_updates", side_effect=CmdRunError("Fuuu"))
    @mock.patch("siun.main.get_config")
    def test_check_with_error_on_get_available_updates(
        self, mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test check CLI command failing to get available updates."""
        mock_get_config.return_value = default_config
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(check, ["-n"])
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        mock_get_available_updates.assert_called_once()
        assert result.exit_code == 1
        assert result.output == ""
        assert result.stderr == "Error: failed to query available updates: Fuuu\n"

    @mock.patch("siun.main.Updates.persist_state")
    @mock.patch("siun.main.Updates.read_state", return_value=STALE_STATE)
    @mock.patch("siun.main._get_available_updates", return_value=["package"])
    @mock.patch("siun.main.get_config")
    def test_check_with_custom_output_format(
        self, mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test check CLI command with custom output format."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check, ["-o", "custom"])
        mock_read_state.assert_called_once()
        mock_persist_state.assert_called_once()
        mock_get_available_updates.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "Updates available: package\n"

    @mock.patch("siun.main.Updates.persist_state")
    @mock.patch("siun.main.Updates.read_state", return_value=False)
    @mock.patch("siun.main._get_available_updates", return_value=["package"])
    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_CUSTOM_STATE_FILE_PATH))
    def test_custom_state_file_path_config(
        self, mock_read_config, mock_get_available_updates, mock_read_state, mock_persist_state
    ):
        """Test check CLI command with custom state file path."""
        runner = CliRunner()
        with mock.patch(
            "siun.config.CONFIG_PATH"
        ):  # NOTE: Required because get_config only tries to read the config file when it exists
            result = runner.invoke(check)

        mock_read_config.assert_called_once()
        mock_read_state.assert_called_once_with(Path("/tmp/siun-test-state.json"))  # noqa: S108
        mock_persist_state.assert_called_once_with(Path("/tmp/siun-test-state.json"))  # noqa: S108
        mock_get_available_updates.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "Updates available\n"

    def test__get_available_updates(self, fp):
        """Test _get_available_updates with cmd being successful."""
        fp.register([":"], stdout="foo\nbar")

        available_updates = _get_available_updates(":")
        assert available_updates == ["foo", "bar"]

    def test__get_available_updates_cmd_fails(self, fp):
        """Test _get_available_updates with cmd failing."""
        fp.register([":"], stdout="foo\nbar")

        with (
            pytest.raises(CmdRunError),
            mock.patch("siun.main.subprocess.run", side_effect=subprocess.CalledProcessError(1, ":")),
        ):
            _get_available_updates(":")

    def test__get_available_updates_cmd_not_found(self, fp):
        """Test _get_available_updates with cmd being not found."""
        fp.register([":"])

        with pytest.raises(CmdRunError), mock.patch("siun.main.subprocess.run", side_effect=FileNotFoundError()):
            _get_available_updates(":")

    @mock.patch("siun.main.Updates.persist_state")
    @mock.patch("siun.main.Updates.read_state", return_value=False)
    @mock.patch("siun.main._update_state", return_value=False)
    def test__get_updates_without_cache_or_update(self, mock__update_state, mock_read_state, mock_persist_state):
        """
        Test _get_updates with no_cache and no_update.

        The CLI should already catch that no_cache and no_update are mutually
        exclusive, but the code shouldn't fail anyway.
        """
        result = _get_updates(
            no_cache=True,
            no_update=True,
            criteria={},
            thresholds={},
            cmd_available="",
            cache_min_age_minutes=0,
            state_file_path=Path("/tmp/siun-test-state.json"),  # noqa: S108
        )
        mock__update_state.assert_not_called()
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        assert result.score == 0

    @mock.patch("siun.main.Updates.persist_state")
    @mock.patch("siun.main.Updates.read_state")
    @mock.patch("siun.main._update_state", return_value=False)
    def test__get_updates_with_no_update_and_existing_cache(
        self, mock__update_state, mock_read_state, mock_persist_state
    ):
        """Test _get_updates with no_update."""
        existing_state = {
            "last_update": {"py-type": "datetime", "value": "1970-01-01T01:00:00Z"},
            "state": {"py-type": "State", "value": "OK"},
            "thresholds": {},
            "matched_criteria": {},
            "available_updates": ["siun"],
            "criteria_settings": {},
        }
        mock_read_state.return_value = existing_state
        result = _get_updates(
            no_cache=False,
            no_update=True,
            criteria={},
            thresholds={},
            cmd_available="",
            cache_min_age_minutes=0,
            state_file_path=Path("/tmp/siun-test-state.json"),  # noqa: S108
        )
        mock__update_state.assert_not_called()
        mock_read_state.assert_called_once()
        mock_persist_state.assert_not_called()
        assert result.available_updates == ["siun"]

    @pytest.mark.feature_notification
    @mock.patch("siun.notification.UpdateNotification.show")
    @mock.patch("siun.main._get_available_updates", return_value=["package"])
    @mock.patch("siun.main.get_config")
    def test_check_notification(self, mock_get_config, mock_get_available_updates, mock_show, config_w_notification):
        """Test check CLI command with notification."""
        mock_get_config.return_value = config_w_notification
        runner = CliRunner()
        result = runner.invoke(check, ["-n"])
        mock_get_available_updates.assert_called_once()
        mock_show.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "Updates available\n"

    @pytest.mark.feature_notification
    @mock.patch("siun.main.Updates.set_last_state")  # Don't update `last_state`, it's already set in the fixture
    @mock.patch("siun.main.Updates.read_state")
    @mock.patch("siun.notification.UpdateNotification.show")
    @mock.patch("siun.main.get_config")
    def test_check_notification_threshold(
        self, mock_get_config, mock_show, mock_read_state, mock_set_last_state, config_w_notification_threshold
    ):
        """Test check CLI command with notification threshold set to `warning`."""
        mock_get_config.return_value = config_w_notification_threshold

        # `available` state is below notification threshold
        mock_read_state.return_value = AVAILABLE_STATE
        runner = CliRunner()
        result = runner.invoke(check, ["-U"])
        mock_show.assert_not_called()
        assert result.exit_code == 0
        assert result.output == "Updates available\n"

        # `warning` state exceeds notification threshold
        mock_read_state.return_value = WARNING_STATE
        runner = CliRunner()
        result = runner.invoke(check, ["-U"])
        mock_show.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "Updates recommended\n"
