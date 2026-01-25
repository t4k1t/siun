"""Module for criteria models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field

CRITERION_REGISTRY: dict[str, type[V2Criterion]] = {}


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
