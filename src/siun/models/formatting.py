"""Formatting models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


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


class FormatObject(BaseModel):
    """Objects for output formatting."""

    available_updates: str
    last_update: str
    matched_criteria: str
    matched_criteria_short: str
    score: int
    status_text: str
    update_count: int
    # Excluded fields won't be usable in custom format
    state_color: str = Field(exclude=True)
    state_name: str = Field(exclude=True)
