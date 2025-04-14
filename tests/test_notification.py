"""Test notification module."""

from unittest import mock

import pytest
from pydantic import ValidationError

from siun.notification import NotificationUrgency, UpdateNotification
from siun.state import FormatObject


class TestNotification:
    """Test UpdateNotification."""

    @mock.patch("siun.notification.UpdateNotification.show")
    def test_defaults_ok(self, mocked_show):
        """Test defaults are enough."""
        notification = UpdateNotification()
        notification.show()

        assert notification.app_name == "siun"
        assert notification.title == "$status_text"
        mocked_show.assert_called_once()

    @pytest.mark.parametrize(
        "urgency, expected_value",
        [
            (None, None),
            ("low", NotificationUrgency.low),
            ("normal", NotificationUrgency.normal),
            ("critical", NotificationUrgency.critical),
        ],
    )
    def test_urgency_validation_ok(self, urgency, expected_value):
        """Test valid urgency values."""
        notification = UpdateNotification(urgency=urgency)

        assert notification.app_name == "siun"
        assert notification.urgency == expected_value

    @pytest.mark.parametrize(
        "urgency",
        ["invalid_string", "", 31415],
    )
    def test_urgency_validation_fail(self, urgency):
        """Test invalid urgency values."""
        with pytest.raises(ValidationError) as error:
            UpdateNotification(urgency=urgency)

        assert error.value.errors()[0]["msg"].startswith("Value error, input should be a valid urgency")

    def test_template_values(self):
        """Test filling of template variables."""
        template_string_all = (
            "$available_updates | $last_update | $matched_criteria | "
            "$matched_criteria_short | $score | $status_text | $update_count"
        )
        format_obj = FormatObject(
            available_updates="siun",
            last_update="2025-04-09T00:00:00+00:00",
            matched_criteria="available",
            matched_criteria_short="av",
            score=2,
            status_text="Updates available",
            update_count=1,
            state_color="green",
            state_name="AVAILABLE_UPDATES",
        )
        notification = UpdateNotification(title="$status_text: $available_updates", message=template_string_all)

        notification.fill_templates(format_obj)

        assert notification.title == "Updates available: siun"
        assert notification.message == "siun | 2025-04-09T00:00:00+00:00 | available | av | 2 | Updates available | 1"
