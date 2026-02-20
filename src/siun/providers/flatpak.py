"""Flatpak package update provider."""

from __future__ import annotations

import subprocess

from pydantic import ConfigDict

from siun.errors import UpdateProviderError
from siun.models import PackageUpdate
from siun.providers.base import UpdateProvider


class UpdateProviderFlatpak(UpdateProvider):
    """Update provider for flatpak."""

    name: str = "flatpak"
    list_apps: bool = True
    list_runtimes: bool = True
    _default_cmds: list[list[str]] = [["flatpak", "remote-ls", "--updates", "--columns=name,version,branch,commit"]]

    def fetch_updates(self) -> list[PackageUpdate]:
        """Get list of updates from flatpak."""
        cmd = self.pick_cmd(self._default_cmds)
        if not self.list_apps:
            cmd.append("--runtime")
        if not self.list_runtimes:
            cmd.append("--app")

        try:
            available_updates_run = subprocess.run(  # noqa: S603
                cmd,
                check=True,
                capture_output=True,
                text=True,
                shell=False,
            )
            return self.parse_updates(available_updates_run.stdout.splitlines(), "")

        except Exception as error:
            message = f"unexpected error: {error}"
            raise UpdateProviderError(message, self.name) from error

    def parse_updates(self, lines: list[str], pattern: str) -> list[PackageUpdate]:
        """Parse list of available update strings into list of PackageUpdate objects."""
        available_updates: list[PackageUpdate] = []
        for line in lines:
            fields = line.split("\t")
            if len(fields) != 4:
                message = f"failed to parse output: {line}"
                raise UpdateProviderError(message, self.name)

            name, version, branch, commit = fields
            available_updates.append(
                PackageUpdate(
                    name=name,
                    old_version=None,
                    new_version=version or branch or commit,
                    provider=self.name,
                )
            )
        return available_updates

    model_config = ConfigDict(extra="forbid")  # pyright: ignore[reportUnannotatedClassAttribute]
