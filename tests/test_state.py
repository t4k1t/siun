"""Test state module."""

import datetime
import io
import json
from os import environ
from pathlib import Path
from unittest import mock

import pytest

from siun.state import State, StateText, Updates, _load_user_criteria, load_state
from siun.util import get_default_criteria_dir


class TestUpdates:
    """Test Updates class."""

    def test_defaults_ok(self, default_config, default_thresholds):
        """Test no available updates."""
        updates = Updates(thresholds_settings=default_thresholds, criteria_settings=default_config.criteria)
        updates.update(available_updates=[])
        result = updates.text_value

        assert result == StateText.OK

    def test_defaults_available(self, default_config, default_thresholds):
        """Test available updates."""
        updates = Updates(thresholds_settings=default_thresholds, criteria_settings=default_config.criteria)
        updates.update(available_updates=["siun"])
        result = updates.text_value

        assert result == StateText.AVAILABLE_UPDATES

    def test_defaults_recommended(self, default_config, default_thresholds):
        """Test recommended updates."""
        updates = Updates(thresholds_settings=default_thresholds, criteria_settings=default_config.criteria)
        updates.update(available_updates=["siun", "linux"])
        result = updates.text_value

        assert result == StateText.WARNING_UPDATES

    def test_defaults_required(self, default_config, default_thresholds):
        """Test required updates."""
        updates = Updates(thresholds_settings=default_thresholds, criteria_settings=default_config.criteria)
        updates.update(available_updates=["siun", "linux", *["package"] * 15])
        result = updates.text_value

        assert result == StateText.CRITICAL_UPDATES

    @mock.patch("siun.state.Path.open")
    def test_read_state(self, mock_open):
        """Test reading existing state."""
        json_content = io.StringIO(
            "{"
            '"last_update": "1970-01-01T01:00:00Z", '
            '"state": "OK", "thresholds": {}, '
            '"matched_criteria": {}, "available_updates": ["siun"], "criteria_settings": {}'
            "}"
        )
        mock_open.return_value = json_content
        mock_file = mock.MagicMock()
        updates = load_state(mock_file)

        assert updates
        assert updates.available_updates == ["siun"]

    @mock.patch("siun.state.Path.open")
    def test_read_state_handles_custom_types(self, mock_open):
        """Test loading state from disk handles custom types."""
        json_content = io.StringIO(
            "{"
            '"last_update": "1970-01-01T01:00:00Z", '
            '"state": "OK", "thresholds": {}, '
            '"matched_criteria": {}, "available_updates": [], "criteria_settings": {}'
            "}"
        )
        mock_open.return_value = json_content
        mock_file = mock.MagicMock()
        updates = load_state(mock_file)

        assert updates
        assert updates.available_updates == []
        assert updates.state == State.OK

    @mock.patch("siun.state.Path.open")
    def test_read_state_handles_deprecated_custom_types(self, mock_open):
        """Test loading state from disk handles custom types."""
        json_content = io.StringIO(
            "{"
            '"last_update": "1970-01-01T01:00:00Z", '
            '"state": {"py-type": "State", "value": "OK"}, "thresholds": {}, '
            '"matched_criteria": {}, "available_updates": [], "criteria_settings": {}'
            "}"
        )
        mock_open.return_value = json_content
        mock_file = mock.MagicMock()
        updates = load_state(mock_file)

        assert updates is None  # Deprecated type is treated like unknown state

    def test_write_state_handles_custom_types(self, tmp_path, default_config, default_thresholds):
        """Test custom types can be serialized to disk."""
        last_update = datetime.datetime.now(tz=datetime.UTC)
        state = State.WARNING_UPDATES
        state_file_path = tmp_path / "test.json"
        updates = Updates(
            thresholds_settings=default_thresholds,
            criteria_settings=default_config.criteria,
            last_update=last_update,
            state=state,
        )
        updates.persist_state(state_file_path=state_file_path)

        content = json.loads(state_file_path.read_text())
        assert datetime.datetime.fromisoformat(content["last_update"]) == last_update
        assert content["state"] == "WARNING_UPDATES"


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
        with mock.patch.dict(environ, clear=True):
            environ["XDG_CONFIG_HOME"] = "/tmp/siun-tests/config"  # noqa: S108
            assert get_default_criteria_dir() == Path("/tmp/siun-tests/config/siun/criteria")  # noqa: S108

    def test__default_criteria_dir_wo_config_home(self):
        with mock.patch.dict(environ, clear=True):
            environ["HOME"] = "/tmp/siun-tests/no_config_home"  # noqa: S108
            assert get_default_criteria_dir() == Path("/tmp/siun-tests/no_config_home/.config/siun/criteria")  # noqa: S108
