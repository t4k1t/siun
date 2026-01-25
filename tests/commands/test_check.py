"""Test check command."""

import datetime
import tempfile
import tomllib
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from siun.cli import _get_updates, check
from siun.errors import ConfigError, UpdateProviderError
from siun.models import CriterionAvailable, CriterionCount, PackageUpdate
from siun.state import Updates

EMPTY_STATE = Updates(
    available_updates=[],
    matched_criteria={},
    last_update=datetime.datetime.now(tz=datetime.UTC),
)

CONFIG_CUSTOM_STATE_FILE_PATH = """
state_dir = "/tmp/siun-test-state"
"""


class TestCheckCommand:
    """Test check command."""

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[],
    )
    @mock.patch("siun.cli_utils.get_config")
    def test_check_no_available_updates_no_cache(
        self, mock_get_config, mock_fetch_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test check CLI command with no updates and --no-cache option."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check, ["-n"])
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        mock_fetch_available_updates.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "No matches.\n"

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[],
    )
    @mock.patch("siun.cli_utils.get_config")
    def test_check_with_config_path_option(
        self, mock_get_config, mockfetch_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test --config-path CLI option."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="r") as config_path:
            result = runner.invoke(check, ["-n", "-C", config_path.name])
            mock_get_config.assert_called_once_with(Path(config_path.name))
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        mockfetch_available_updates.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "No matches.\n"

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[],
    )
    @mock.patch("siun.cli_utils.get_config")
    def test_check_no_cache_no_update_options(
        self, mock_get_config, mockfetch_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test check CLI command with --no-cache and --no-update options."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check, ["-n", "--no-update"])
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        mockfetch_available_updates.assert_not_called()
        assert result.exit_code == 1
        assert result.output == "Error: --no-update and --no-cache options are mutually exclusive\n"

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[],
    )
    @mock.patch("siun.cli_utils.get_config")
    def test_check_quiet_option(
        self, mock_get_config, mockfetch_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test check CLI command with no updates and --quiet option."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check, ["-n", "-q"])
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        mockfetch_available_updates.assert_called_once()
        assert result.exit_code == 0
        assert result.output == ""

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[],
    )
    @mock.patch("siun.cli_utils.get_config")
    def test_check_no_updates(
        self, mock_get_config, mockfetch_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test check CLI command with no updates."""
        mock_read_state.return_value = EMPTY_STATE
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check)
        mock_read_state.assert_called_once()
        mock_persist_state.assert_not_called()
        mockfetch_available_updates.assert_not_called()
        assert result.exit_code == 0
        assert result.output == "No matches.\n"

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[],
    )
    @mock.patch("siun.cli_utils.get_config", side_effect=ConfigError("failed", config_path=Path("/path/to/siun.toml")))
    def test_check_invalid_config(
        self, mock_get_config, mockfetch_available_updates, mock_read_state, mock_persist_state, default_config
    ):
        """Test get_state CLI command with invalid config."""
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check)
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        mockfetch_available_updates.assert_not_called()
        assert result.exit_code == 1
        assert result.output == "Error: failed; config path: /path/to/siun.toml\n"

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[PackageUpdate(name="package")],
    )
    @mock.patch("siun.cli_utils.get_config")
    def test_check_stale_state(
        self,
        mock_get_config,
        mockfetch_available_updates,
        mock_read_state,
        mock_persist_state,
        default_config,
        state_stale,
    ):
        """Test check CLI command with stale state on disk."""
        mock_read_state.return_value = state_stale
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check)
        mock_read_state.assert_called_once()
        mock_persist_state.assert_called_once()
        mockfetch_available_updates.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "Updates available\n"

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        side_effect=UpdateProviderError("Permission denied", "pacman"),
    )
    @mock.patch("siun.cli_utils.get_config")
    def test_check_with_error_onfetch_available_updates(
        self,
        mock_get_config,
        mockfetch_available_updates,
        mock_read_state,
        mock_persist_state,
        default_config,
        state_stale,
    ):
        """Test check CLI command failing to get available updates."""
        mock_read_state.return_value = state_stale
        mock_get_config.return_value = default_config
        runner = CliRunner()
        result = runner.invoke(check, ["-n"])
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        mockfetch_available_updates.assert_called_once()
        assert result.exit_code == 1
        assert result.stdout == ""
        assert result.stderr == "Error: failed to query available updates: Permission denied\n"

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[PackageUpdate(name="package")],
    )
    @mock.patch("siun.cli_utils.get_config")
    def test_check_with_custom_output_format(
        self,
        mock_get_config,
        mockfetch_available_updates,
        mock_read_state,
        mock_persist_state,
        v2_config_w_custom_format,
        state_stale,
    ):
        """Test check CLI command with custom output format."""
        mock_read_state.return_value = state_stale
        mock_get_config.return_value = v2_config_w_custom_format
        runner = CliRunner()
        result = runner.invoke(check, ["-o", "custom"])
        mock_read_state.assert_called_once()
        mock_persist_state.assert_called_once()
        mockfetch_available_updates.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "Updates available: package\n"

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state", return_value=False)
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[PackageUpdate(name="package")],
    )
    @mock.patch("siun.config._read_config", return_value=tomllib.loads(CONFIG_CUSTOM_STATE_FILE_PATH))
    def test_custom_state_file_path_config(
        self, mock_read_config, mockfetch_available_updates, mock_read_state, mock_persist_state
    ):
        """Test check CLI command with custom state file path."""
        mock_read_state.return_value = False
        runner = CliRunner()
        with mock.patch(
            "siun.config.get_default_config_dir"
        ):  # NOTE: Required because get_config only tries to read the config file when it exists
            result = runner.invoke(check)

        mock_read_config.assert_called_once()
        mock_read_state.assert_called_once_with(Path("/tmp/siun-test-state/state.json"))  # noqa: S108
        mock_persist_state.assert_called_once_with(Path("/tmp/siun-test-state/state.json"))  # noqa: S108
        mockfetch_available_updates.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "Updates available\n"

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state", return_value=False)
    @mock.patch("siun.cli.update_state_with_available_packages", return_value=False)
    def test__get_updates_without_cache_or_update(self, mock__update_state, mock_read_state, mock_persist_state):
        """
        Test _get_updates with no_cache and no_update.

        The CLI should already catch that no_cache and no_update are mutually
        exclusive, but the code shouldn't fail anyway.
        """
        mock_read_state.return_value = False
        result = _get_updates(
            no_cache=True,
            no_update=True,
            criteria=[],
            thresholds=[],
            update_provider="dummy",
            cache_min_age_minutes=0,
            state_file_path=Path("/tmp/siun-test-state.json"),  # noqa: S108
        )
        mock__update_state.assert_not_called()
        mock_read_state.assert_not_called()
        mock_persist_state.assert_not_called()
        assert result.score == 0

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch("siun.cli.update_state_with_available_packages", return_value=False)
    def test__get_updates_with_no_update_and_existing_cache(
        self, mock__update_state, mock_read_state, mock_persist_state
    ):
        """Test _get_updates with no_update."""
        config_criteria = [
            CriterionAvailable(name="available", weight=1),
            CriterionCount(name="count", weight=2, count=1),
        ]
        existing_state = Updates(
            last_update="1970-01-01T01:00:00Z",
            state="OK",
            thresholds=[],
            matched_criteria={},
            available_updates=[{"name": "siun"}],
            criteria_settings=[],
        )
        mock_read_state.return_value = existing_state
        result = _get_updates(
            no_cache=False,
            no_update=True,
            criteria=config_criteria,
            thresholds=[],
            update_provider="dummy",
            cache_min_age_minutes=0,
            state_file_path=Path("/tmp/siun-test-state.json"),  # noqa: S108
        )
        mock__update_state.assert_not_called()
        mock_read_state.assert_called_once()
        mock_persist_state.assert_not_called()
        assert result.available_updates == [PackageUpdate(name="siun")]

    @mock.patch("siun.cli.INSTALLED_FEATURES", [])
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[PackageUpdate(name="package")],
    )
    @mock.patch("siun.cli_utils.get_config")
    def test_check_notification_wo_feature(self, mock_get_config, mockfetch_available_updates, config_w_notification):
        """Test check CLI command with missing notification feature."""
        mock_get_config.return_value = config_w_notification
        runner = CliRunner()
        result = runner.invoke(check, ["-n"])
        mockfetch_available_updates.assert_called_once()
        assert result.exit_code == 1
        assert result.stderr.startswith("Error: notifications require the 'notification' feature") is True

    @pytest.mark.feature_notification
    @mock.patch("siun.notification.UpdateNotification.show")
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[PackageUpdate(name="package")],
    )
    @mock.patch("siun.cli_utils.get_config")
    def test_check_notification(self, mock_get_config, mockfetch_available_updates, mock_show, config_w_notification):
        """Test check CLI command with notification."""
        mock_get_config.return_value = config_w_notification
        runner = CliRunner()
        result = runner.invoke(check, ["-n"])
        mockfetch_available_updates.assert_called_once()
        mock_show.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "Updates available\n"

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.providers.UpdateProviderPacman.fetch_updates", return_value=[PackageUpdate(name="siun")])
    @mock.patch("siun.cli.load_state")
    @mock.patch("siun.notification.UpdateNotification.show")
    @mock.patch("siun.cli_utils.get_config")
    def test_check_notification_below_threshold(
        self,
        mock_get_config,
        mock_show,
        mock_read_state,
        mock_get_updates,
        mock_persist_state,
        config_w_notification_threshold,
        state_stale,
    ):
        """Test state below threshold does not show notification."""
        mock_get_config.return_value = config_w_notification_threshold
        # `available` state is below notification threshold
        mock_read_state.return_value = state_stale
        runner = CliRunner()
        result = runner.invoke(check)
        mock_show.assert_not_called()
        assert result.exit_code == 0
        assert result.output == "Updates available\n"

    @pytest.mark.feature_notification
    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch(
        "siun.providers.UpdateProviderPacman.fetch_updates",
        return_value=[PackageUpdate(name="package"), PackageUpdate(name="other_package")],
    )
    @mock.patch("siun.cli.load_state")
    @mock.patch("siun.notification.UpdateNotification.show")
    @mock.patch("siun.cli_utils.get_config")
    def test_check_notification_above_threshold(
        self,
        mock_get_config,
        mock_show,
        mock_read_state,
        mock_get_updates,
        mock_persist_state,
        config_w_notification_threshold,
        state_stale,
    ):
        """Test state gte threshold shows notification."""
        mock_get_config.return_value = config_w_notification_threshold
        # `warning` state exceeds notification threshold
        mock_read_state.return_value = state_stale
        runner = CliRunner()
        result = runner.invoke(check)
        assert result.output == "Updates recommended\n"
        mock_show.assert_called_once()
        assert result.exit_code == 0
        assert result.output == "Updates recommended\n"
