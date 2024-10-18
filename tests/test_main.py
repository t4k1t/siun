import datetime
from pathlib import Path
from subprocess import CalledProcessError
from unittest import mock

from click.testing import CliRunner

from siun.errors import CmdRunError, ConfigError
from siun.main import check
from siun.state import SiunState, State

EMPTY_STATE = SiunState(
    criteria_settings={},
    thresholds={},
    available_updates=[],
    matched_criteria={},
    state=State.OK,
    last_update=datetime.datetime.now(tz=datetime.timezone.utc),
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
    last_update=datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=1),
)


@mock.patch("siun.main.Updates.persist_state")
@mock.patch("siun.main.Updates.read_state")
@mock.patch("siun.main._get_available_updates", return_value=[])
@mock.patch("siun.main.get_config")
def test_check_no_available_updates_no_cache(
    mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
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
    mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
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
    mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
):
    """Test check CLI command with no updates and --quiet-cache option."""
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
    mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
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
    mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
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
    mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
):
    """Test check CLI command with no updates."""
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
    mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
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
@mock.patch("siun.main.subprocess.run", side_effect=CalledProcessError(returncode=123, cmd="cmd", stderr="Fuuu"))
@mock.patch("siun.main.get_config")
def test_check_with_error_in_get_available_updates_cmd(
    mock_get_config, mock_get_available_updates, mock_read_state, mock_persist_state, default_config
):
    """Test get_available_updates cmd failing with an error."""
    mock_get_config.return_value = default_config
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(check, ["-n"])
    mock_read_state.assert_not_called()
    mock_persist_state.assert_not_called()
    mock_get_available_updates.assert_called_once()
    assert result.exit_code == 1
    assert result.output == ""
    assert result.stderr == "Error: failed to query available updates: Fuuu\n"
