"""Available update providers module."""

from __future__ import annotations

import re
import subprocess

from pydantic import BaseModel, ConfigDict

from siun.errors import UpdateProviderError
from siun.models import PackageUpdate

UPDATE_PROVIDER_REGISTRY: dict[str, type[UpdateProvider]] = {}
PACMAN_PATTERN: str = (
    r"^(?P<name>[_\-0-9a-z]+)\s+(?P<old_version>[\-\.\:0-9a-z]+)\s+\-\>\s+(?P<new_version>[\-\.\:0-9a-z]+)$"
)


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
                )
            )

        return available_updates

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Register subclass in criterion registry."""
        super.__init_subclass__(**kwargs)
        UPDATE_PROVIDER_REGISTRY[cls.name] = cls

    model_config = ConfigDict(extra="allow")  # pyright: ignore[reportUnannotatedClassAttribute]


class UpdateProviderPacman(UpdateProvider):
    """Update provider for pacman."""

    name: str = "pacman"
    cmd: list[str] = ["pacman", "-Qu"]
    pattern: str = PACMAN_PATTERN

    def fetch_updates(self) -> list[PackageUpdate]:
        """Get list of updates from pacman."""
        try:
            available_updates_run = subprocess.run(  # noqa: S603
                self.cmd,
                check=True,
                capture_output=True,
                text=True,
                shell=False,
            )
            return self.parse_updates(available_updates_run.stdout.splitlines(), self.pattern)

        except subprocess.CalledProcessError as error:
            if error.returncode == 1:
                # When no updates are available, pacman returns exit code 1
                return []
        except Exception as error:
            message = f"unexpected error: {error}"
            raise UpdateProviderError(message, self.name) from error

        return []

    model_config = ConfigDict(extra="forbid")  # pyright: ignore[reportUnannotatedClassAttribute]


class UpdateProviderGeneric(UpdateProvider):
    """Update provider for generic shell command."""

    name: str = "generic"
    cmd: list[str] = []
    pattern: str = r"(?P<name>.+)"  # Match anything to group 'name'

    def fetch_updates(self) -> list[PackageUpdate]:
        """Get list of updates from generic shell command."""
        try:
            available_updates_run = subprocess.run(  # noqa: S603
                self.cmd,
                check=True,
                capture_output=True,
                text=True,
                shell=False,
            )
            return self.parse_updates(available_updates_run.stdout.splitlines(), self.pattern)
        except Exception as error:
            message = f"unexpected error: {error}"
            raise UpdateProviderError(message, self.name) from error

    model_config = ConfigDict(extra="forbid")  # pyright: ignore[reportUnannotatedClassAttribute]
