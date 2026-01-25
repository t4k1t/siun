"""Pacman package update provider."""

from __future__ import annotations

import subprocess

from pydantic import ConfigDict

from siun.errors import UpdateProviderError
from siun.models import PackageUpdate
from siun.providers.base import UpdateProvider

PACMAN_PATTERN: str = (
    r"^(?P<name>[\+_\-\.0-9a-z]+)\s+(?P<old_version>[\+_\-\.\:0-9a-z]+)\s+\-\>\s+(?P<new_version>[\+_\-\.\:0-9a-z\+]+)$"
)


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
