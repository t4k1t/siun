"""Collection of test fixtures."""

from pathlib import Path

import pytest

from siun.config import SiunConfig, Threshold


@pytest.fixture(scope="module")
def default_thresholds():
    """Provide default thresholds."""
    return {Threshold.available: 1, Threshold.warning: 2, Threshold.critical: 3}


@pytest.fixture(scope="module")
def default_config(default_thresholds):
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
            "count_threshold": 15,
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
