"""Base package update provider and update provider registry."""

from __future__ import annotations

import re
from shutil import which

from pydantic import BaseModel, ConfigDict

from siun.errors import UpdateProviderError
from siun.models import PackageUpdate

UPDATE_PROVIDER_REGISTRY: dict[str, type[UpdateProvider]] = {}


class UpdateProvider(BaseModel):
    """Base provider for available updates."""

    name: str

    def fetch_updates(self) -> list[PackageUpdate]:
        """Scaffolding for fetching list of available updates."""
        raise NotImplementedError

    def parse_updates(self, lines: list[str], pattern: str) -> list[PackageUpdate]:
        """Parse list of available update strings into list of PackageUpdate objects."""
        available_updates: list[PackageUpdate] = []
        for line in lines:
            match = re.match(pattern, line)
            if not match or "name" not in match.groupdict():
                message = f"failed to parse output: {line}"
                raise UpdateProviderError(message, self.name)

            match_dict = match.groupdict()
            available_updates.append(
                PackageUpdate(
                    name=match_dict["name"],
                    old_version=match_dict.get("old_version"),
                    new_version=match_dict.get("new_version"),
                    provider=self.name,
                )
            )

        return available_updates

    def pick_cmd(self, cmds: list[list[str]]) -> list[str]:
        """Pick the first available command from the list."""
        print("pick")
        for cmd in cmds:
            if which(cmd[0]) is not None:
                return cmd

        message = f"no suitable command found among: {cmds}"
        raise UpdateProviderError(message, self.name)

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Register subclass in criterion registry."""
        super.__init_subclass__(**kwargs)
        UPDATE_PROVIDER_REGISTRY[cls.name] = cls

    model_config = ConfigDict(extra="allow")  # pyright: ignore[reportUnannotatedClassAttribute]
