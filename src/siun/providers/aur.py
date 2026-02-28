"""AUR package update provider."""

from __future__ import annotations

import subprocess

from pydantic import ConfigDict

from siun.errors import UpdateProviderError
from siun.models import PackageUpdate
from siun.providers.base import UpdateProvider
from siun.providers.pacman import PACMAN_PATTERN


class UpdateProviderAur(UpdateProvider):
    """Update provider for AUR helpers."""

    name: str = "aur"
    _default_cmds: list[list[str]] = [["aur-check-updates"], ["paru", "--aur", "-Qu"]]
    pattern: str = PACMAN_PATTERN
    exit_code_no_updates: int = 1

    def fetch_updates(self) -> list[PackageUpdate]:
        """Get list of updates from AUR helper."""
        cmd = self.pick_cmd(self._default_cmds)
        try:
            available_updates_run = subprocess.run(  # noqa: S603
                cmd,
                check=True,
                capture_output=True,
                text=True,
                shell=False,
            )
            return self.parse_updates(available_updates_run.stdout.splitlines(), self.pattern)

        except subprocess.CalledProcessError as error:
            # pacman and some AUR helpers return exit code 1 when there are no updates
            if error.returncode != self.exit_code_no_updates:
                raise
        except Exception as error:
            message = f"unexpected error: {error}"
            raise UpdateProviderError(message, self.name) from error

        return []

    model_config = ConfigDict(extra="forbid")
