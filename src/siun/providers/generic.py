"""Generic package update provider."""

from __future__ import annotations

import subprocess

from pydantic import ConfigDict

from siun.errors import UpdateProviderError
from siun.models import PackageUpdate
from siun.providers.base import UpdateProvider


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

    model_config = ConfigDict(extra="forbid")
