import pytest

from siun.state import StateText, Updates


class TestUpdates:
    """Test Updates class."""

    def test_defaults_ok(self, default_config, default_thresholds):
        """Test no available updates."""
        updates = Updates(thresholds=default_thresholds, criteria_settings=default_config["criteria"])
        updates.update(available_updates=[])
        result = updates.text_value

        assert result == StateText.OK

    def test_defaults_available(self, default_config, default_thresholds):
        """Test available updates."""
        updates = Updates(thresholds=default_thresholds, criteria_settings=default_config["criteria"])
        updates.update(available_updates=["siun"])
        result = updates.text_value

        assert result == StateText.AVAILABLE_UPDATES

    def test_defaults_recommended(self, default_config, default_thresholds):
        """Test recommended updates."""
        updates = Updates(thresholds=default_thresholds, criteria_settings=default_config["criteria"])
        updates.update(available_updates=["siun", "linux"])
        result = updates.text_value

        assert result == StateText.WARNING_UPDATES

    def test_defaults_required(self, default_config, default_thresholds):
        """Test required updates."""
        updates = Updates(thresholds=default_thresholds, criteria_settings=default_config["criteria"])
        updates.update(available_updates=["siun", "linux", *["package"] * 15])
        result = updates.text_value

        assert result == StateText.CRITICAL_UPDATES


@pytest.fixture
def default_config():
    """Provide default config."""
    return {
        "cmd_available": "pacman -Quq",
        "criteria": {
            "available_weight": 1,
            "critical_pattern": "^archlinux-keyring$|^linux$|^firefox$|^pacman.*$",
            "critical_weight": 1,
            "count_threshold": 15,
            "count_weight": 1,
            "lastupdate_age_hours": 618,  # 7 days
            "lastupdate_weight": 1,
        },
    }


@pytest.fixture
def default_thresholds():
    """Provide default thresholds."""
    return {
        0: StateText.OK.name,
        1: StateText.AVAILABLE_UPDATES.name,
        2: StateText.WARNING_UPDATES.name,
        3: StateText.CRITICAL_UPDATES.name,
    }
