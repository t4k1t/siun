"""Collection of test fixtures."""

import datetime
from pathlib import Path
from unittest import mock

import pytest

from siun.config import SiunConfig, get_default_thresholds
from siun.models import CriterionAvailable, CriterionCount, CriterionPattern, V2Threshold
from siun.state import FormatObject, Updates


@pytest.fixture(scope="module")
def default_thresholds():
    """Provide default thresholds."""
    return get_default_thresholds()


@pytest.fixture(scope="module")
def default_config(default_thresholds):
    """Provide default config."""
    return SiunConfig(
        cmd_available="pacman -Quq; if [ $? == 1 ]; then :; fi",
        cache_min_age_minutes=30,
        v2_thresholds=default_thresholds,
        v2_criteria=[
            CriterionAvailable(name="available", weight=1),
            CriterionPattern(name="pattern", weight=1, pattern="^archlinux-keyring$|^linux$|^pacman.*$"),
            CriterionCount(name="count", weight=1, count=15),
        ],
        custom_format="$status_text: $available_updates",
        state_file=Path("/tmp/siun-tests/.local/state/siun/state.json"),  # noqa: S108
    )


@pytest.fixture(scope="module")
def config_w_notification(default_thresholds):
    """Provide default config."""
    return SiunConfig(
        cmd_available="pacman -Quq",
        cache_min_age_minutes=30,
        thresholds=default_thresholds,
        v2_criteria=[
            CriterionAvailable(name="available", weight=1),
            CriterionPattern(name="pattern", weight=1, pattern="^archlinux-keyring$|^linux$|^pacman.*$"),
            CriterionCount(name="count", weight=1, count=2),
        ],
        custom_format="$status_text: $available_updates",
        state_file=Path("/tmp/siun-tests/.local/state/siun/state.json"),  # noqa: S108
        notification={"title": "siun test notification", "threshold": "available"},
    )


@pytest.fixture(scope="module")
def config_w_notification_threshold(default_thresholds):
    """Provide default config."""
    return SiunConfig(
        cmd_available="pacman -Quq",
        cache_min_age_minutes=30,
        thresholds=default_thresholds,
        v2_criteria=[
            CriterionAvailable(name="available", weight=1),
            CriterionPattern(name="pattern", weight=1, pattern="^archlinux-keyring$|^linux$|^pacman.*$"),
            CriterionCount(name="count", weight=1, count=2),
        ],
        custom_format="$status_text: $available_updates",
        state_file=Path("/tmp/siun-tests/.local/state/siun/state.json"),  # noqa: S108
        notification={"title": "siun test notification", "threshold": "warning"},
    )


@pytest.fixture(scope="module")
def v2_config_w_custom_format(default_thresholds):
    """Provide default config."""
    return SiunConfig(
        cmd_available="pacman -Quq; if [ $? == 1 ]; then :; fi",
        cache_min_age_minutes=30,
        v2_thresholds=[V2Threshold(score=1, name="available", text="Updates available")],
        v2_criteria=[
            CriterionAvailable(name="available", weight=1),
            CriterionCount(name="count", weight=1, count=15),
            CriterionPattern(name="pattern", weight=1, pattern="^archlinux-keyring$|^linux$|^pacman.*$"),
        ],
        custom_format="$status_text: $available_updates",
        state_file=Path("/tmp/siun-tests/.local/state/siun/state.json"),  # noqa: S108
    )


@pytest.fixture
def state_stale(default_thresholds):
    """Expired Update state."""
    return Updates(
        criteria_settings=[
            CriterionAvailable(name="available", weight=1),
            CriterionCount(name="count", weight=1, count=2),
        ],
        thresholds_settings=default_thresholds,
        available_updates=[],
        last_update=datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1),
    )


@pytest.fixture
def notification_mock():
    """Provide a mock notification object for tests."""

    def _make(threshold="warning", urgency=None):
        notification = mock.Mock()
        notification.threshold = threshold
        notification.urgency = urgency
        notification.hints = {}
        notification.fill_templates = mock.Mock()
        notification.show = mock.Mock()
        return notification

    return _make


@pytest.fixture(scope="module")
def format_object_ok():
    """FormatObject with 'Ok' status."""
    return FormatObject(
        available_updates="",
        last_update="2025-01-01T00:00:00+00:00",
        matched_criteria="",
        matched_criteria_short="",
        score=0,
        status_text="Ok",
        update_count=0,
        state_color="green",
        state_name="Ok",
    )


@pytest.fixture(scope="module")
def format_object_available():
    """FormatObject with 'Updates available' status."""
    return FormatObject(
        available_updates="",
        last_update="2025-01-01T00:00:00+00:00",
        matched_criteria="",
        matched_criteria_short="",
        score=0,
        status_text="Updates available",
        update_count=0,
        state_color="blue",
        state_name="Updates available",
    )


@pytest.fixture(scope="module")
def format_object_recommended():
    """FormatObject with 'Updates recommended' status."""
    return FormatObject(
        available_updates="",
        last_update="2025-01-01T00:00:00+00:00",
        matched_criteria="",
        matched_criteria_short="",
        score=0,
        status_text="Updates recommended",
        update_count=0,
        state_color="yellow",
        state_name="Updates recommended",
    )


@pytest.fixture(scope="module")
def format_object_required():
    """FormatObject with 'Updates required' status."""
    return FormatObject(
        available_updates="",
        last_update="2025-01-01T00:00:00+00:00",
        matched_criteria="",
        matched_criteria_short="",
        score=0,
        status_text="Updates required",
        update_count=0,
        state_color="red",
        state_name="Updates required",
    )


@pytest.fixture
def format_object_factory():
    """Build factory for FormatObject instances with custom attributes."""

    def _make(**kwargs):
        defaults = {
            "available_updates": "",
            "last_update": "2025-01-01T00:00:00+00:00",
            "matched_criteria": "",
            "matched_criteria_short": "",
            "score": 0,
            "status_text": "Ok",
            "update_count": 0,
            "state_color": "green",
            "state_name": "Ok",
        }
        defaults.update(kwargs)
        return FormatObject(**defaults)

    return _make
