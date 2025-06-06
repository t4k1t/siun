"""Config module."""

import shutil
from collections.abc import Mapping
from pathlib import Path
from tomllib import TOMLDecodeError
from tomllib import load as toml_load
from typing import Any, no_type_check

from pydantic import BaseModel, Field, field_validator

from siun.errors import ConfigError
from siun.notification import UpdateNotification
from siun.state import Threshold
from siun.util import get_default_config_dir, get_default_state_path


class SiunConfig(BaseModel):
    """Config struct."""

    cmd_available: str = Field(default="pacman -Quq")
    cache_min_age_minutes: int = Field(default=30)
    thresholds: dict[Threshold, int] = Field(
        default={Threshold.available: 1, Threshold.warning: 2, Threshold.critical: 3}
    )
    criteria: dict[str, Any]
    custom_format: str = Field(default="$status_text: $available_updates")
    state_file: Path = Field(default_factory=get_default_state_path)
    notification: UpdateNotification | None = Field(default=None)

    @field_validator("criteria")
    def criteria_must_have_weight(
        cls,  # noqa: N805: first arg is the SiunConfig class, not an instance
        value: dict[str, Any],
    ) -> dict[str, Any]:
        """Check if all criteria have a configured weight."""
        names: set[str] = set()
        for key in value:
            if "_" in key:
                names.add(key.split("_")[0])

        missing_weights: list[str] = []
        for name in names:
            if f"{name}_weight" not in value:
                missing_weights.append(name)
        if missing_weights:
            message = f"missing weight for criteria: {', '.join(missing_weights)}"
            raise ValueError(message)

        return value


def _read_config(config_path: Path) -> dict[str, Any]:  # pragma: no cover
    """Read config from disk."""
    with Path.open(config_path, "rb") as file_obj:
        return toml_load(file_obj)


@no_type_check
def _update_nested(d: dict, u: dict | Mapping) -> dict:
    """
    Preserve existing keys of nested dicts.

    https://stackoverflow.com/a/3233356
    """
    for k, v in u.items():
        if isinstance(v, Mapping):
            d[k] = _update_nested(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def _migrate_legacy_config(config_path: Path):
    legacy_config_path = Path().home() / ".config" / "siun.toml"
    if not config_path.exists() and legacy_config_path.exists() and legacy_config_path.is_file():
        shutil.copy2(legacy_config_path, config_path)


def get_config(config_path: Path | None = None) -> SiunConfig:
    """Get config from defaults and user supplied values."""
    if config_path is None:
        config_path = get_default_config_dir() / Path("config.toml")
    _migrate_legacy_config(config_path)
    # NOTE: `criteria` setting doesn't get its default value from the model
    # because we want to allow partial configuration
    config_dict: dict[str, Any] = {
        "criteria": {
            "available_weight": 1,
            "critical_pattern": "^archlinux-keyring$|^linux$|^pacman.*$",
            "critical_weight": 1,
            "count_threshold": 15,
            "count_weight": 1,
            "lastupdate_age_hours": 618,  # 7 days
            "lastupdate_weight": 1,
        },
    }
    if config_path.exists() and config_path.is_file():
        try:
            user_config = _read_config(config_path)
            config_dict = _update_nested(config_dict, user_config)
        except OSError as error:
            message = f"failed to open config file for reading: {error}"
            raise ConfigError(message, config_path) from error
        except TOMLDecodeError as error:
            message = f"provided config file not valid: {error}"
            raise ConfigError(message, config_path) from error

    config = SiunConfig(**config_dict)
    return config
