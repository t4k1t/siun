"""Test main function and CLI."""

import datetime
from pathlib import Path
from unittest import mock

import pytest

from siun.cli import _get_updates, _handle_notification
from siun.errors import SiunNotificationError
from siun.models import CriterionAvailable, CriterionCount
from siun.state import Updates


class TestMain:
    """Test main function."""

    @mock.patch("siun.cli.INSTALLED_FEATURES", set())
    def test__handle_notification_missing_feature(self, notification_mock):
        """Test _handle_notification raises SiunNotificationError if feature missing."""
        notification = notification_mock("warning")
        config = mock.Mock()
        config.notification = notification
        config.mapped_thresholds = {"warning": mock.Mock(score=10)}
        state = mock.Mock()
        state.match = mock.Mock(score=15)
        state.last_match = None
        state.format_object = {}

        with pytest.raises(SiunNotificationError) as excinfo:
            _handle_notification(config, state)
        assert "notifications require the 'notification' feature" in str(excinfo.value)

    @mock.patch("siun.cli.INSTALLED_FEATURES", {"notification"})
    def test__handle_notification_threshold_logic(self, notification_mock):
        """Test _handle_notification does not show notification if match.score <= threshold_score."""
        notification = notification_mock("warning")
        config = mock.Mock()
        config.notification = notification
        config.mapped_thresholds = {"warning": mock.Mock(score=10)}
        state = mock.Mock()
        state.match = mock.Mock(score=8)
        state.last_match = None
        state.format_object = {}

        _handle_notification(config, state)
        notification.show.assert_not_called()

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch("siun.cli.update_state_with_available_packages", return_value=None)
    def test_existing_state_sets_required_fields(
        self, mock_update_state, mock_load_state, mock_persist_state, v2_config_w_custom_format, updates_single
    ):
        """Test loaded state receives required values from config."""
        loaded_state = Updates(
            criteria_settings=[],
            thresholds=[],
            available_updates=[updates_single],
            matched_criteria={},
            last_update=datetime.datetime.now(tz=datetime.UTC),
        )
        mock_load_state.return_value = loaded_state

        config_criteria = [
            CriterionAvailable(name="available", weight=1),
            CriterionCount(name="count", weight=2, count=1),
        ]

        result = _get_updates(
            no_cache=False,
            no_update=True,
            update_providers=["dummy"],
            criteria=config_criteria,
            thresholds=v2_config_w_custom_format.v2_thresholds,
            cache_min_age_minutes=10,
            state_file_path=Path("/tmp/siun-test-state.json"),  # noqa: S108
        )

        assert result.criteria_settings == config_criteria
        assert result.thresholds == v2_config_w_custom_format.v2_thresholds
        assert result.available_updates == [updates_single]

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch("siun.cli.update_state_with_available_packages", return_value=None)
    def test__get_updates_persist_state_on_match_change(
        self, mock_update_state, mock_load_state, mock_persist_state, default_thresholds
    ):
        """Test persist_state called when last_match != match."""
        threshold1 = default_thresholds[0]
        threshold2 = default_thresholds[-1]

        def evaluate_side_effect(self, available_updates):
            self.match = threshold2  # new match

        with mock.patch("siun.state.Updates.evaluate", evaluate_side_effect):
            state = Updates(
                criteria_settings=[],
                thresholds=[threshold1, threshold2],
                available_updates=[],
                matched_criteria={},
                last_update=datetime.datetime.now(tz=datetime.UTC),
                match=threshold1,
                last_match=threshold2,
            )
            mock_load_state.return_value = state

            _get_updates(
                no_cache=False,
                no_update=False,
                update_providers=["dummy"],
                criteria=[],
                thresholds=[threshold1, threshold2],
                cache_min_age_minutes=10,
                state_file_path=Path("/tmp/siun-test-state.json"),  # noqa: S108
            )

        mock_persist_state.assert_called_once()

    @mock.patch("siun.cli.Updates.persist_state")
    @mock.patch("siun.cli.load_state")
    @mock.patch("siun.cli.update_state_with_available_packages", return_value=None)
    def test__get_updates_no_persist_state_when_match_unchanged(
        self, mock_update_state, mock_load_state, mock_persist_state, default_thresholds
    ):
        """Test persist_state not called when last_match == match."""
        threshold = default_thresholds[0]

        def evaluate_side_effect(self, available_updates):
            pass  # match remains unchanged

        with mock.patch("siun.state.Updates.evaluate", evaluate_side_effect):
            state = Updates(
                criteria_settings=[],
                thresholds=[threshold],
                available_updates=[],
                matched_criteria={},
                last_update=datetime.datetime.now(tz=datetime.UTC),
                match=threshold,
                last_match=threshold,
            )
            mock_load_state.return_value = state

            _get_updates(
                no_cache=False,
                no_update=False,
                update_providers=["dummy"],
                criteria=[],
                thresholds=[threshold],
                cache_min_age_minutes=10,
                state_file_path=Path("/tmp/siun-test-state.json"),  # noqa: S108
            )

        mock_persist_state.assert_not_called()
