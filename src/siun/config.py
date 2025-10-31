"""Config module."""

import shutil
from pathlib import Path
from tomllib import TOMLDecodeError
from tomllib import load as toml_load
from typing import Any, Self

from pydantic import BaseModel, Field, ValidationError, computed_field, field_validator, model_validator

from siun.errors import ConfigError
from siun.models import (
    CRITERION_REGISTRY,
    ClickColor,
    CriterionAvailable,
    CriterionCount,
    CriterionCustom,
    CriterionPattern,
    V2Criterion,
    V2Threshold,
)
from siun.notification import UpdateNotification
from siun.util import get_default_config_dir, get_default_state_path


def get_default_thresholds() -> list[V2Threshold]:
    """Backwards compatible default thresholds."""
    return [
        V2Threshold(name="critical", score=3, color=ClickColor.red, text="Updates required"),
        V2Threshold(name="warning", score=2, color=ClickColor.yellow, text="Updates recommended"),
        V2Threshold(name="available", score=1, color=ClickColor.green, text="Updates available"),
    ]


def get_default_criteria() -> list[V2Criterion]:
    """Backwards compatible default criteria."""
    return [
        CriterionAvailable(name="available", weight=1),
        CriterionPattern(name="pattern", weight=1, pattern="^archlinux-keyring$|^linux$|^pacman.*$"),
        CriterionCount(name="count", weight=1, count=15),
    ]


# TODO: Fail if old config values are found so users can fix their configs
class SiunConfig(BaseModel):
    """Config struct."""

    cmd_available: str = Field(default="pacman -Quq; if [ $? == 1 ]; then :; fi")
    cache_min_age_minutes: int = Field(default=30)
    v2_thresholds: list[V2Threshold] = Field(default_factory=get_default_thresholds)
    v2_criteria: list[V2Criterion] = Field(default_factory=get_default_criteria)
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

    @computed_field
    @property
    def mapped_thresholds(self) -> dict[str, V2Threshold]:
        """Map thresholds to threshold name."""
        return {t.name: t for t in self.v2_thresholds}

    @model_validator(mode="after")
    def notification_must_reference_threshold(self) -> Self:
        """Check if notification threshold exists."""
        value = getattr(self, "notification", None)
        thresholds: list[str] = [t.name for t in getattr(self, "v2_thresholds", [])]

        if value and value.threshold not in thresholds:
            message = f"notification.threshold must be one of: {', '.join(thresholds)}"
            raise ValueError(message)

        return self

    @field_validator("v2_criteria")
    def transform_criteria(cls, value: list[V2Criterion]) -> list[V2Criterion]:
        """Transform criteria to subclasses of V2Criterion."""
        criteria: list[V2Criterion] = []
        for crit in value:
            model_cls = CRITERION_REGISTRY.get(crit.name)
            if model_cls:
                # Builtin criterion
                criteria.append(model_cls(**crit.model_dump(exclude={"name_short"})))
            else:
                # Custom criterion
                criteria.append(CriterionCustom(**crit.model_dump(exclude={"name_short"})))

        return criteria

    @field_validator("v2_thresholds")
    def thresholds_must_have_unique_name(cls, value: list[V2Threshold]) -> list[V2Threshold]:
        """
        Check if all thresholds have a unique name.

        The name doubles as ID.
        """
        unique_names = {obj.name for obj in value}
        if len(unique_names) != len(value):
            message = "each threshold must have a unique name."
            raise ValueError(message)

        return value


def _read_config(config_path: Path) -> dict[str, Any]:  # pragma: no cover
    """Read config from disk."""
    with Path.open(config_path, "rb") as file_obj:
        return toml_load(file_obj)


def _migrate_legacy_config(config_path: Path):
    legacy_config_path = Path().home() / ".config" / "siun.toml"
    if not config_path.exists() and legacy_config_path.exists() and legacy_config_path.is_file():
        shutil.copy2(legacy_config_path, config_path)


def _format_error_loc(err_loc: tuple[int | str, ...]):
    if err_loc:
        return f"'{'.'.join([str(loc) for loc in err_loc])}': "
    return ""


def _format_pydantic_error(error: ValidationError):
    return "; ".join([f"{_format_error_loc(err['loc'])}{err['msg']}" for err in error.errors()])


def get_config(config_path: Path | None = None) -> SiunConfig:
    """Get config from defaults and user supplied values."""
    if config_path is None:
        config_path = get_default_config_dir() / Path("config.toml")
    _migrate_legacy_config(config_path)
    config_dict: dict[str, Any] = {}
    if config_path.exists() and config_path.is_file():
        try:
            config_dict = _read_config(config_path)
        except OSError as error:
            message = f"failed to open config file for reading: {error}"
            raise ConfigError(message, config_path) from error
        except TOMLDecodeError as error:
            message = f"provided config file not valid: {error}"
            raise ConfigError(message, config_path) from error
    else:
        message = f"config file not found: {config_path}\nPlease create a configuration file."
        raise ConfigError(message, config_path)

    try:
        config = SiunConfig(**config_dict)
    except ValidationError as error:
        message = f"invalid configuration: {_format_pydantic_error(error)}"
        raise ConfigError(message, config_path) from error

    return config
