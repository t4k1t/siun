"""Config module."""

import shutil
from collections.abc import Mapping
from pathlib import Path
from tomllib import TOMLDecodeError
from tomllib import load as toml_load
from typing import Any, no_type_check

from pydantic import BaseModel, Field, computed_field, field_validator

from siun.errors import ConfigError
from siun.models import V2Threshold
from siun.notification import UpdateNotification
from siun.util import get_default_config_dir, get_default_state_path


def get_default_thresholds() -> list[V2Threshold]:
    """Backwards compatible default thresholds."""
    return [
        V2Threshold(name="critical", score=3, color="red"),
        V2Threshold(name="warning", score=2, color="yellow"),
        V2Threshold(name="available", score=1, color="green"),
    ]


class SiunConfig(BaseModel):
    """Config struct."""

    cmd_available: str = Field(default="pacman -Quq; if [ $? == 1 ]; then :; fi")
    cache_min_age_minutes: int = Field(default=30)
    v2_thresholds: list[V2Threshold] = Field(default_factory=get_default_thresholds)
    criteria: dict[str, Any]
    custom_format: str = Field(default="$status_text: $available_updates")
    state_file: Path = Field(default_factory=get_default_state_path)
    notification: UpdateNotification | None = Field(default=None)

    @computed_field
    @property
    def sorted_thresholds(self) -> list[V2Threshold]:
        """
        Sort thresholds by descending score.

        This makes it easier to find the highest threshold that matches later.
        """
        return sorted(self.v2_thresholds, key=lambda item: item.score, reverse=True)

    @field_validator("v2_thresholds")
    def thresholds_must_have_unique_name(cls, value: list[V2Threshold]) -> list[V2Threshold]:
        """
        Check if all thresholds have a unique name.

        The name doubles as ID.
        """
        unique_names = {obj.name for obj in value}
        if len(unique_names) != len(value):
            message = "each thresholds must have a unique name."
            raise ValueError(message)

        return value

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
