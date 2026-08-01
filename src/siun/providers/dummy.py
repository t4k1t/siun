"""Dummy package update provider."""

from __future__ import annotations

from pydantic import ConfigDict

from siun.models import PackageUpdate
from siun.providers.base import UpdateProvider


class UpdateProviderDummy(UpdateProvider):
    """Update provider for dummy data."""

    name: str = "dummy"
    cmd: list[str] = []
    pattern: str = r"(?P<name>.+)"  # Match anything to group 'name'

    def fetch_updates(self) -> list[PackageUpdate]:
        """Get dummy list of updates."""
        return [
            PackageUpdate(name="linux", provider="dummy"),
            PackageUpdate(name="siun", provider="dummy"),
            PackageUpdate(name="battered", provider="dummy"),
            PackageUpdate(name="python", provider="dummy"),
        ]

    model_config = ConfigDict(extra="forbid")
