"""Formatting models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


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


@dataclass()
class FormatObject:
    """Objects for output formatting."""

    available_updates: str
    last_update: str
    matched_criteria: str
    matched_criteria_short: str
    score: int
    status_text: str
    update_count: int
    state_color: str
    state_name: str

    def to_template_vars(self) -> dict[str, object]:
        """Expose template vars only."""
        data = asdict(self)

        # Internal fields only
        data.pop("state_color")
        data.pop("state_name")

        return data
