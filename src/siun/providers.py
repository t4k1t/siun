"""Available update providers module."""

from __future__ import annotations

import re
import subprocess

from pydantic import BaseModel, ConfigDict

from siun.models import PackageUpdate

UPDATE_PROVIDER_REGISTRY: dict[str, type[UpdateProvider]] = {}


class UpdateProvider(BaseModel):
    """Base provider for available updates."""

    name: str

    model_config = ConfigDict(extra="allow")  # pyright: ignore[reportUnannotatedClassAttribute]

    def fetch_updates(self) -> list[PackageUpdate]:
        """Scaffolding for fetching list of available updates."""
        raise NotImplementedError

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Register subclass in criterion registry."""
        super.__init_subclass__(**kwargs)
        UPDATE_PROVIDER_REGISTRY[cls.name] = cls


class UpdateProviderPacman(UpdateProvider):
    """Update provider for pacman."""

    name: str = "pacman"
    cmd: list[str] = ["pacman", "-Qu"]
    # TODO: Decide if pattern should be overridable
    pattern: str = r"^([a-z_\-]+)\s+([0-9\-\.]+)\s+\-\>\s+([0-9\-\.]+)$"

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
            available_updates: list[PackageUpdate] = []
            for line in available_updates_run.stdout.splitlines():
                match = re.match(self.pattern, line)
                if not match:
                    return available_updates

                available_updates.append(
                    PackageUpdate(name=match.group(1), old_version=match.group(2), new_version=match.group(3))
                )
            return available_updates

        except subprocess.CalledProcessError as error:
            if error.returncode == 1:
                # When no updates are available, pacman returns exit code 1
                return []

        return []

    model_config = ConfigDict(extra="forbid")  # pyright: ignore[reportUnannotatedClassAttribute]


class UpdateProviderGeneric(UpdateProvider):
    """Update provider for generic shell command."""

    name: str = "generic"
    cmd: list[str] = []
    # TODO: Document how pattern is used
    pattern: str = r"^([a-z_\-]+)\s+([0-9\-\.]+)\s+\-\>\s+([0-9\-\.]+)$"

    def fetch_updates(self) -> list[PackageUpdate]:
        """Get list of updates from generic shell command."""
        # TODO: Document change to `shell=False` for generic provider
        available_updates_run = subprocess.run(  # noqa: S603
            self.cmd,
            check=True,
            capture_output=True,
            text=True,
            shell=False,
        )
        available_updates: list[PackageUpdate] = []
        for line in available_updates_run.stdout.splitlines():
            match = re.match(self.pattern, line)
            if not match:
                return available_updates

            # TODO: Gracefully handle partial pattern matches; Especially the case that only a list of names is provided
            available_updates.append(
                PackageUpdate(name=match.group(1), old_version=match.group(2), new_version=match.group(3))
            )
        return available_updates

    model_config = ConfigDict(extra="forbid")  # pyright: ignore[reportUnannotatedClassAttribute]
