"""Test state module."""

import io
import subprocess
from os import environ
from pathlib import Path
from unittest import mock

import pytest

from siun.errors import CmdRunError, CriterionError
from siun.state import FormatObject, Updates, _load_user_criteria, fetch_available_updates, load_state
from siun.util import get_default_criteria_dir


class TestUpdates:
    """Test Updates class."""

    def test_defaults_ok(self, default_config, default_thresholds):
        """Test no available updates."""
        updates = Updates(thresholds=default_thresholds, criteria_settings=default_config.criteria)
        updates.evaluate(available_updates=[])
        result = updates.text_value

        assert result == "No matches."

    def test_defaults_available(self, default_config, default_thresholds):
        """Test available updates."""
        updates = Updates(thresholds=default_thresholds, criteria_settings=default_config.criteria)
        updates.evaluate(available_updates=["siun"])
        result = updates.text_value

        assert result == "Updates available"

    def test_defaults_recommended(self, default_config, default_thresholds):
        """Test recommended updates."""
        updates = Updates(thresholds=default_thresholds, criteria_settings=default_config.criteria)
        updates.evaluate(available_updates=["siun", "linux"])
        result = updates.text_value

        assert result == "Updates recommended"

    def test_defaults_required(self, default_config, default_thresholds):
        """Test required updates."""
        updates = Updates(thresholds=default_thresholds, criteria_settings=default_config.criteria)
        updates.evaluate(available_updates=["siun", "linux", *["package"] * 15])
        result = updates.text_value

        assert result == "Updates required"

    @mock.patch("siun.state.Path.open")
    def test_read_state(self, mock_open):
        """Test reading existing state."""
        json_content = io.StringIO(
            "{"
            '"last_update": "1970-01-01T01:00:00Z", '
            '"state": "OK", "thresholds": [], '
            '"matched_criteria": {}, "available_updates": ["siun"], "criteria_settings": {}'
            "}"
        )
        mock_open.return_value = json_content
        mock_file = mock.MagicMock()
        updates = load_state(mock_file)

        assert updates
        assert updates.available_updates == ["siun"]

    @mock.patch("siun.state.Path.open")
    def test_read_state_handles_deprecated_types(self, mock_open):
        """Test loading state from disk handles custom types."""
        # `state` is deprecated
        json_content = io.StringIO(
            "{"
            '"last_update": "1970-01-01T01:00:00Z", '
            '"state": "OK", "thresholds": [], '
            '"matched_criteria": {}, "available_updates": [], "criteria_settings": {}'
            "}"
        )
        mock_open.return_value = json_content
        mock_file = mock.MagicMock()
        updates = load_state(mock_file)

        assert updates
        assert updates.available_updates == []
        assert updates.match is None

    @mock.patch("siun.state.Path.open")
    def test_read_state_handles_deprecated_custom_types(self, mock_open):
        """Test loading state from disk handles custom types."""
        # `py-type` struct is deprecated
        json_content = io.StringIO(
            "{"
            '"last_update": "1970-01-01T01:00:00Z", '
            '"state": {"py-type": "State", "value": "OK"}, "thresholds": [], '
            '"matched_criteria": {}, "available_updates": [], "criteria_settings": {}'
            "}"
        )
        mock_open.return_value = json_content
        mock_file = mock.MagicMock()
        updates = load_state(mock_file)

        assert updates.match is None  # Deprecated type is treated like unknown state

    def test_load_state_file_missing(self, tmp_path):
        """Test loading state if state file does not exist."""
        state_file = tmp_path / "siun-missing.json"
        result = load_state(state_file)

        assert result is None

    def test_update_raises_criterion_error_on_user_criteria_failure(
        self, default_config, default_thresholds, monkeypatch
    ):
        """Test Updates.update raises CriterionError if user criteria loading fails."""
        updates = Updates(thresholds=default_thresholds, criteria_settings=default_config.criteria)

        def fail_loader(**kwargs):
            raise RuntimeError("fail!")  # noqa: EM101

        monkeypatch.setattr("siun.state._load_user_criteria", fail_loader)
        with pytest.raises(CriterionError) as excinfo:
            updates.evaluate(available_updates=["siun"])

        assert "unable to load user criteria" in str(excinfo.value)

    def test_format_object_populated(self, default_config, default_thresholds):
        """Test format_object returns correct values for populated state."""
        updates = Updates(thresholds=default_thresholds, criteria_settings=default_config.criteria)
        updates.available_updates = ["siun", "linux"]
        updates.matched_criteria = {"available": {"weight": 1}, "count": {"weight": 2}}
        updates.match = default_thresholds[1]  # Assume at least two thresholds
        fmt = updates.format_object
        assert isinstance(fmt, FormatObject)
        assert fmt.available_updates == "siun, linux"
        assert fmt.matched_criteria == "available, count"
        assert fmt.matched_criteria_short == "av,co"
        assert fmt.score == 3
        assert fmt.status_text == updates.text_value
        assert fmt.update_count == 2


class TestCustomCriteria:
    """Test custom criteria."""

    def test_load_custom_criterion(self, tmp_path):
        """Test custom criteria can be loaded."""
        criteria_settings = {"test_criterion_weight": 2}
        include_path = tmp_path / "criteria"
        include_path.mkdir()
        criterion_content = """class SiunCriterion:
    def is_fullfilled(self, criteria_settings, available_updates):
        return True
        """
        with Path.open(include_path / Path("test_criterion.py"), "w+") as criterion_file:
            criterion_file.write(criterion_content)
        user_criteria = _load_user_criteria(criteria_settings=criteria_settings, include_path=include_path)
        assert user_criteria
        assert "test_criterion" in user_criteria

    @pytest.mark.parametrize("criteria_settings", [{"test_criterion_weight": 0}, {}])
    def test_custom_criterion_not_loaded_wo_weight(self, tmp_path, criteria_settings):
        """Test custom criteria not getting loaded without a configured weight."""
        include_path = tmp_path / "criteria"
        include_path.mkdir()
        criterion_content = """class SiunCriterion:
    def is_fullfilled(self, criteria_settings, available_updates):
        return True
        """
        with Path.open(include_path / Path("test_criterion.py"), "w+") as criterion_file:
            criterion_file.write(criterion_content)
        user_criteria = _load_user_criteria(criteria_settings=criteria_settings, include_path=include_path)
        assert isinstance(user_criteria, dict)
        assert "test_criterion" not in user_criteria

    def test__default_criteria_dir(self):
        """Test get_default_criteria_dir with XDG_CONFIG_HOME set."""
        with mock.patch.dict(environ, clear=True):
            environ["XDG_CONFIG_HOME"] = "/tmp/siun-tests/config"  # noqa: S108
            assert get_default_criteria_dir() == Path("/tmp/siun-tests/config/siun/criteria")  # noqa: S108

    def test__default_criteria_dir_wo_config_home(self):
        """Test get_default_criteria_dir without XDG_CONFIG_HOME set."""
        with mock.patch.dict(environ, clear=True):
            environ["HOME"] = "/tmp/siun-tests/no_config_home"  # noqa: S108
            assert get_default_criteria_dir() == Path("/tmp/siun-tests/no_config_home/.config/siun/criteria")  # noqa: S108


class TestState:
    """Test other state module functions."""

    def test_fetch_available_updates(self, fp):
        """Test fetch_available_updates with cmd being successful."""
        fp.register([":"], stdout="foo\nbar")

        available_updates = fetch_available_updates(":")
        assert available_updates == ["foo", "bar"]

    def test_fetch_available_updates_cmd_fails(self, fp):
        """Test fetch_available_updates with cmd failing."""
        fp.register([":"], stdout="foo\nbar")

        with (
            pytest.raises(CmdRunError),
            mock.patch("siun.state.subprocess.run", side_effect=subprocess.CalledProcessError(1, ":")),
        ):
            fetch_available_updates(":")

    def test_fetch_available_updates_cmd_not_found(self, fp):
        """Test fetch_available_updates with cmd being not found."""
        fp.register([":"])

        with pytest.raises(CmdRunError), mock.patch("siun.state.subprocess.run", side_effect=FileNotFoundError()):
            fetch_available_updates(":")
