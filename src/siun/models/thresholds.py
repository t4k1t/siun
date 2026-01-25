"""Threshold models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from siun.models.formatting import ClickColor


class V2Threshold(BaseModel):
    """Version 2 of the Threshold struct."""

    score: int
    name: str
    text: str
    color: ClickColor = ClickColor.reset

    model_config = ConfigDict(extra="forbid")  # pyright: ignore[reportUnannotatedClassAttribute]
