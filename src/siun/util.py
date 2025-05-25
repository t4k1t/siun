"""Common utils."""

from os import environ
from pathlib import Path


def get_default_state_path() -> Path:
    """
    Provide default value for state_file setting.

    By default, siun will try the following in order:
    1. `$XDG_STATE_HOME/siun/state.json`
    2. `$HOME/.local/state/siun/state.json`
    """
    return Path(environ.get("XDG_STATE_HOME", Path.home() / Path(".local/state"))) / Path("siun/state.json")


def get_default_config_dir() -> Path:
    """
    Provide default value for criteria_path setting.

    By default, siun will try the following in order:
    1. `$XDG_CONFIG_HOME/siun`
    2. `$HOME/.config/siun`
    """
    return Path(environ.get("XDG_CONFIG_HOME", Path.home() / Path(".config"))) / Path("siun")


def get_default_criteria_dir() -> Path:
    """
    Provide default value for criteria_path setting.

    By default, siun will try the following in order:
    1. `$XDG_CONFIG_HOME/siun/criteria`
    2. `$HOME/.config/siun/criteria`
    """
    return get_default_config_dir() / Path("criteria")
