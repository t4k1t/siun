"""Module for siun data structures."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field

CRITERION_REGISTRY: dict[str, type[V2Criterion]] = {}


class ClickColor(Enum):
    """Colors supported by click 8.3."""

    black = "black"
    red = "red"
    green = "green"
    yellow = "yellow"
    blue = "blue"
    magenta = "magenta"
    cyan = "cyan"
    white = "white"
    bright_black = "bright_black"
    bright_red = "bright_red"
    bright_green = "bright_green"
    bright_yellow = "bright_yellow"
    bright_blue = "bright_blue"
    bright_magenta = "bright_magenta"
    bright_cyan = "bright_cyan"
    bright_white = "bright_white"
    reset = "reset"


class V2Threshold(BaseModel):
    """Version 2 of the Threshold struct."""

    score: int
    name: str
    text: str
    color: ClickColor = ClickColor.reset

    model_config = ConfigDict(extra="forbid")  # pyright: ignore[reportUnannotatedClassAttribute]


class V2Criterion(BaseModel):
    """Version 2 of the Criterion struct."""

    name: str
    short_name: str | None = Field(default=None)
    weight: int

    model_config = ConfigDict(extra="allow")  # pyright: ignore[reportUnannotatedClassAttribute]

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Register subclass in criterion registry."""
        super.__init_subclass__(**kwargs)
        CRITERION_REGISTRY[cls.name] = cls

    @computed_field
    @property
    def name_short(self) -> str:
        """Get short name for formatters."""
        if self.short_name is None:
            return self.name[:2]

        return self.short_name


class CriterionAvailable(V2Criterion):
    """
    Criterion for available updates.

    Considered a match if any updates are available.
    """

    name: str = "available"


class CriterionCount(V2Criterion):
    """
    Criterion for number of available updates.

    Considered a match if number of available updates equals, or exceeds `count`.
    """

    name: str = "count"
    count: int

    model_config = ConfigDict(extra="forbid")  # pyright: ignore[reportUnannotatedClassAttribute]


class CriterionArchaudit(V2Criterion):
    """
    Criterion for updates flagged by archaudit.

    Considered a match if archaudit flags any of the available updates, and a fix for the issue is available.
    """

    name: str = "archaudit"
    model_config = ConfigDict(extra="forbid")  # pyright: ignore[reportUnannotatedClassAttribute]


class CriterionPattern(V2Criterion):
    """
    Criterion for updates matching pattern.

    Considered a match if any of the available updates match the provided pattern.
    """

    name: str = "pattern"
    pattern: str

    model_config = ConfigDict(extra="forbid")  # pyright: ignore[reportUnannotatedClassAttribute]


class CriterionCustom(V2Criterion):
    """Criterion for custom criteria."""

    name: str = "custom"
    model_config = ConfigDict(extra="allow")  # pyright: ignore[reportUnannotatedClassAttribute]


class PackageUpdate(BaseModel):
    """Struct representing an available update."""

    name: str
    old_version: str | None = None
    new_version: str | None = None

    model_config = ConfigDict(extra="allow")  # pyright: ignore[reportUnannotatedClassAttribute]
