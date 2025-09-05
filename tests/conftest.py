"""Collection of test fixtures."""

import datetime
from pathlib import Path

import pytest

from siun.config import SiunConfig, Threshold
from siun.state import State, Updates


@pytest.fixture(scope="module")
def default_thresholds():
    """Provide default thresholds."""
    return {Threshold.available: 1, Threshold.warning: 2, Threshold.critical: 3}


@pytest.fixture(scope="module")
def default_config(default_thresholds):
    """Provide default config."""
    return SiunConfig(
        cmd_available="pacman -Quq; if [ $? == 1 ]; then :; fi",
        cache_min_age_minutes=30,
        thresholds=default_thresholds,
        criteria={
            "available_weight": 1,
            "critical_pattern": "^archlinux-keyring$|^linux$|^pacman.*$",
            "critical_weight": 1,
            "count_threshold": 15,
            "count_weight": 1,
            "lastupdate_age_hours": 618,  # 7 days
            "lastupdate_weight": 1,
        },
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
        criteria={
            "available_weight": 1,
            "critical_pattern": "^archlinux-keyring$|^linux$|^pacman.*$",
            "critical_weight": 1,
            "count_threshold": 2,
            "count_weight": 1,
            "lastupdate_age_hours": 618,  # 7 days
            "lastupdate_weight": 1,
        },
        custom_format="$status_text: $available_updates",
        state_file=Path("/tmp/siun-tests/.local/state/siun/state.json"),  # noqa: S108
        notification={"title": "siun test notification"},
    )


@pytest.fixture(scope="module")
def config_w_notification_threshold(default_thresholds):
    """Provide default config."""
    return SiunConfig(
        cmd_available="pacman -Quq",
        cache_min_age_minutes=30,
        thresholds=default_thresholds,
        criteria={
            "available_weight": 1,
            "critical_pattern": "^archlinux-keyring$|^linux$|^pacman.*$",
            "critical_weight": 1,
            "count_threshold": 15,
            "count_weight": 1,
            "lastupdate_age_hours": 618,  # 7 days
            "lastupdate_weight": 1,
        },
        custom_format="$status_text: $available_updates",
        state_file=Path("/tmp/siun-tests/.local/state/siun/state.json"),  # noqa: S108
        notification={"title": "siun test notification", "threshold": "warning"},
    )


@pytest.fixture
def state_stale(default_thresholds):
    return Updates(
        criteria_settings={
            "available_weight": 1,
            "critical_weight": 0,
            "count_weight": 1,
            "count_threshold": 2,
            "lastupdate_weight": 0,
        },
        thresholds_settings=default_thresholds,
        available_updates=[],
        matched_criteria={"available": {"weight": 1}},
        state=State.AVAILABLE_UPDATES,
        last_update=datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1),
    )
