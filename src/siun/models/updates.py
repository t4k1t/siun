"""Models dealing with package updates."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PackageUpdate(BaseModel):
    """Struct representing an available update."""

    name: str
    old_version: str | None = None
    new_version: str | None = None
    provider: str

    model_config = ConfigDict(extra="allow")
