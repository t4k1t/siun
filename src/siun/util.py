"""Common utils."""

import shutil
import stat
import tempfile
from os import environ
from pathlib import Path


def get_default_state_dir() -> Path:
    """
    Provide default value for state_dir setting.

    By default, siun will try the following in order:
    1. `$XDG_STATE_HOME/siun/state.json`
    2. `$HOME/.local/state/siun/state.json`
    """
    return Path(environ.get("XDG_STATE_HOME", Path.home() / Path(".local/state"))) / Path("siun")


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


def safely_write_to_disk(*, content: str, target_path: Path) -> None:
    """
    Safely write to disk.

    Avoids partially written state file (and therefore invalid JSON) by
    creating a temporary file first and only replacing the state file once
    the writing operation is done.
    """
    if not Path.exists(target_path.parent):
        # Create parent directory for state file path if it doesn't exist
        Path.mkdir(Path(target_path.parent), parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(mode="w+") as update_file:
        update_file.write(content)
        update_file.flush()
        shutil.copy(update_file.name, target_path)


def is_path_world_writable(path: Path) -> bool:
    """Check if a given path is world-writable."""
    return bool(path.stat().st_mode & stat.S_IWOTH)
