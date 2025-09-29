"""Module for siun data structures."""

from enum import Enum

from pydantic import BaseModel, ConfigDict


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
