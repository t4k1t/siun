from unittest import mock

import pytest

from siun.formatting import Formatter
from siun.state import State, Updates


class TestFormatter:
    """Test Formatter class."""

    @pytest.mark.parametrize(
        "state,expected_output",
        [
            (State.OK, "Ok"),
            (State.AVAILABLE_UPDATES, "Updates available"),
            (State.WARNING_UPDATES, "Updates recommended"),
            (State.CRITICAL_UPDATES, "Updates required"),
        ],
    )
    def test_plain(self, state, expected_output):
        """Test plain formatter."""
        updates = Updates(criteria_settings={}, thresholds_settings={})
        updates.state = state
        formatter = Formatter()

        output, output_kwargs = formatter.format_plain(updates)
        assert output == expected_output
        assert output_kwargs == {}

    @pytest.mark.parametrize(
        "state,expected_output,expected_kwargs",
        [
            (State.OK, "Ok", {"fg": "green"}),
            (State.AVAILABLE_UPDATES, "Updates available", {"fg": "blue"}),
            (State.WARNING_UPDATES, "Updates recommended", {"fg": "yellow"}),
            (State.CRITICAL_UPDATES, "Updates required", {"fg": "red"}),
        ],
    )
    def test_fancy(self, state, expected_output, expected_kwargs):
        """Test fancy formatter."""
        updates = Updates(criteria_settings={}, thresholds_settings={})
        updates.state = state
        formatter = Formatter()

        output, output_kwargs = formatter.format_fancy(updates)
        assert output == expected_output
        assert output_kwargs == expected_kwargs

    @pytest.mark.parametrize(
        "state,expected_output,expected_kwargs",
        [
            (State.OK, '{"count": 0, "text_value": "Ok", "score": 0}', {}),
            (State.AVAILABLE_UPDATES, '{"count": 0, "text_value": "Updates available", "score": 0}', {}),
            (State.WARNING_UPDATES, '{"count": 0, "text_value": "Updates recommended", "score": 0}', {}),
            (State.CRITICAL_UPDATES, '{"count": 0, "text_value": "Updates required", "score": 0}', {}),
        ],
    )
    def test_json(self, state, expected_output, expected_kwargs):
        """Test JSON formatter."""
        updates = Updates(criteria_settings={}, thresholds_settings={})
        updates.state = state
        formatter = Formatter()

        output, output_kwargs = formatter.format_json(updates)
        assert output == expected_output
        assert output_kwargs == expected_kwargs

    def test_json_handles_count_correctly(self):
        """Test count for JSON formatter."""
        updates = Updates(criteria_settings={}, thresholds_settings={})
        updates.state = State.WARNING_UPDATES
        with mock.patch.object(updates, "available_updates", ["package"] * 42):
            formatter = Formatter()

            output, output_kwargs = formatter.format_json(updates)
            assert output == '{"count": 42, "text_value": "Updates recommended", "score": 0}'
            assert output_kwargs == {}

    def test_json_handles_score_correctly(self):
        """Test score for JSON formatter."""
        updates = Updates(criteria_settings={}, thresholds_settings={})
        updates.state = State.WARNING_UPDATES
        updates.matched_criteria = {"available": {"weight": 1}, "critical": {"weight": 2}}
        with mock.patch.object(updates, "available_updates", ["package", "important-package"]):
            formatter = Formatter()

            output, output_kwargs = formatter.format_json(updates)
            assert output == '{"count": 2, "text_value": "Updates recommended", "score": 3}'
            assert output_kwargs == {}

    @pytest.mark.parametrize(
        "state,expected_output,expected_kwargs",
        [
            (State.OK, '{"icon": "archive", "state": "Idle", "text": ""}', {}),
            (State.AVAILABLE_UPDATES, '{"icon": "archive", "state": "Idle", "text": ""}', {}),
            (State.WARNING_UPDATES, '{"icon": "archive", "state": "Warning", "text": ""}', {}),
            (State.CRITICAL_UPDATES, '{"icon": "archive", "state": "Critical", "text": ""}', {}),
        ],
    )
    def test_i3status(self, state, expected_output, expected_kwargs):
        """Test JSON formatter."""
        updates = Updates(criteria_settings={}, thresholds_settings={})
        updates.state = state
        formatter = Formatter()

        output, output_kwargs = formatter.format_i3status(updates)
        assert output == expected_output
        assert output_kwargs == expected_kwargs

    def test_i3status_builds_text_correctly(self):
        """Test score for JSON formatter."""
        updates = Updates(criteria_settings={}, thresholds_settings={})
        updates.state = State.WARNING_UPDATES
        updates.matched_criteria = {"available": {"weight": 1}, "critical": {"weight": 2}}
        with mock.patch.object(updates, "available_updates", ["package", "important-package"]):
            formatter = Formatter()

            output, output_kwargs = formatter.format_i3status(updates)
            assert output == '{"icon": "archive", "state": "Warning", "text": "av,cr"}'
            assert output_kwargs == {}
