import datetime
import io
import json
from unittest import mock

import pytest

from siun.state import State, StateText, Updates, _load_user_criteria


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

    @mock.patch("siun.state.open")
    def test_read_state(self, mock_open):
        """Test required updates."""
        json_content = io.StringIO(
            '{'
                '"last_update": {"py-type": "datetime", "value": "1970-01-01T01:00:00Z"}, '
                '"state": {"py-type": "State", "value": "OK"}, "thresholds": {}, '
                '"matched_criteria": {}, "available_updates": ["siun"], "criteria_settings": {}'
            '}'
        )
        mock_open.return_value = json_content
        mock_file = mock.MagicMock()
        updates = Updates.read_state(mock_file)

        assert updates
        assert updates.available_updates == ["siun"]

    @mock.patch("siun.state.open")
    def test_read_state_handles_custom_types(self, mock_open):
        """Test loading state from disk handles custom types."""
        json_content = io.StringIO(
            '{'
                '"last_update": {"py-type": "datetime", "value": "1970-01-01T01:00:00Z"}, '
                '"state": {"py-type": "State", "value": "OK"}, "thresholds": {}, '
                '"matched_criteria": {}, "available_updates": [], "criteria_settings": {}'
            '}'
        )
        mock_open.return_value = json_content
        mock_file = mock.MagicMock()
        updates = Updates.read_state(mock_file)

        assert updates
        assert updates.available_updates == []
        assert updates.state == State.OK

    def test_write_state_handles_custom_types(self, tmp_path, default_config, default_thresholds):
        """Test custom types can be serialized to disk."""
        last_update = datetime.datetime.now(tz=datetime.UTC)
        state = State.WARNING_UPDATES
        update_file_path = tmp_path / "test.json"
        updates = Updates(
            thresholds_settings=default_thresholds,
            criteria_settings=default_config.criteria,
            last_update=last_update,
            state=state,
        )
        updates.persist_state(update_file_path=update_file_path)

        content = json.loads(update_file_path.read_text())
        assert content["last_update"]["py-type"] == "datetime"
        assert content["state"]["py-type"] == "State"

    def test_load_custom_criterion(self, tmp_path):
        """Test custom criteria can be loaded."""
        criteria_settings = {"test_criterion_weight": 2}
        include_path = tmp_path / "criteria"
        include_path.mkdir()
        criterion_content = """class SiunCriterion:
    def is_fullfilled(self, criteria_settings, available_updates):
        return True
        """
        with open(include_path / "test_criterion.py", "w+") as criterion_file:
            criterion_file.write(criterion_content)
        user_criteria = _load_user_criteria(criteria_settings=criteria_settings, include_path=include_path)
        assert user_criteria
        assert "test_criterion" in user_criteria.keys()

    @pytest.mark.parametrize("criteria_settings", [{"test_criterion_weight": 0}, {}])
    def test_custom_criterion_not_loaded_wo_weight(self, tmp_path, criteria_settings):
        """Test custom criteria not getting loaded if they won't have a configured weight."""
        include_path = tmp_path / "criteria"
        include_path.mkdir()
        criterion_content = """class SiunCriterion:
    def is_fullfilled(self, criteria_settings, available_updates):
        return True
        """
        with open(include_path / "test_criterion.py", "w+") as criterion_file:
            criterion_file.write(criterion_content)
        user_criteria = _load_user_criteria(criteria_settings=criteria_settings, include_path=include_path)
        assert isinstance(user_criteria, dict)
        assert "test_criterion" not in user_criteria.keys()
