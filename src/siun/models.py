"""Module for siun data structures."""

from pydantic import BaseModel, ConfigDict


class V2Threshold(BaseModel):
    """Version 2 of the Threshold struct."""

    score: int
    name: str
    text: str = ""
    color: str | None = None

    model_config = ConfigDict(extra="forbid")  # pyright: ignore[reportUnannotatedClassAttribute]
