"""Flatpak package update provider."""

from __future__ import annotations

import subprocess

from pydantic import ConfigDict

from siun.errors import UpdateProviderError
from siun.models import PackageUpdate
from siun.providers.base import UpdateProvider


class UpdateProviderFlatpak(UpdateProvider):
    """Update provider for Flatpak."""

    name: str = "flatpak"
    list_apps: bool = True
    list_runtimes: bool = True
    _installed_cmds: list[list[str]] = [["flatpak", "list", "--columns=ref,version"]]
    _updates_cmds: list[list[str]] = [["flatpak", "remote-ls", "--updates", "--columns=ref,name,version,branch,commit"]]

    def fetch_updates(self) -> list[PackageUpdate]:
        """Get list of updates from Flatpak."""
        installed_cmd = [*self.pick_cmd(self._installed_cmds)]
        updates_cmd = [*self.pick_cmd(self._updates_cmds)]

        if not self.list_apps:
            installed_cmd.append("--runtime")
            updates_cmd.append("--runtime")
        if not self.list_runtimes:
            installed_cmd.append("--app")
            updates_cmd.append("--app")

        try:
            installed_updates_run = subprocess.run(  # noqa: S603
                installed_cmd,
                check=True,
                capture_output=True,
                text=True,
                shell=False,
            )
            available_updates_run = subprocess.run(  # noqa: S603
                updates_cmd,
                check=True,
                capture_output=True,
                text=True,
                shell=False,
            )
            installed_versions = self._parse_installed_versions(installed_updates_run.stdout.splitlines())
            available_updates = self._parse_available_updates(available_updates_run.stdout.splitlines())

            package_updates: list[PackageUpdate] = []
            for update in available_updates:
                ref = update["ref"]
                new_version = update["version"] or update["branch"] or update["commit"] or None
                package_updates.append(
                    PackageUpdate(
                        name=update["name"] or ref,
                        old_version=installed_versions.get(ref),
                        new_version=new_version,
                        provider=self.name,
                    )
                )

            return package_updates

        except Exception as error:
            message = f"unexpected error: {error}"
            raise UpdateProviderError(message, self.name) from error

    def _split_line(self, *, line: str, num_fields: int) -> list[str]:
        fields = line.split("\t")
        if len(fields) > num_fields:
            message = f"failed to parse output: {line}"
            raise UpdateProviderError(message, self.name)

        return fields

    def _parse_installed_versions(self, lines: list[str]) -> dict[str, str]:
        installed_versions: dict[str, str] = {}
        for line in lines:
            if not line.strip():
                continue

            fields = self._split_line(line=line, num_fields=2)
            ref = fields[0]
            version = fields[1] if len(fields) == 2 else ""
            if not ref:
                message = f"failed to parse output: {line}"
                raise UpdateProviderError(message, self.name)

            if version:
                installed_versions[ref] = version

        return installed_versions

    def _parse_available_updates(self, lines: list[str]) -> list[dict[str, str]]:
        available_updates: list[dict[str, str]] = []
        for line in lines:
            if not line.strip():
                continue

            fields = self._split_line(line=line, num_fields=5)
            fields += [""] * (5 - len(fields))
            ref, name, version, branch, commit = fields
            if not ref:
                message = f"failed to parse output: {line}"
                raise UpdateProviderError(message, self.name)

            if not branch:
                ref_parts = ref.rsplit("/", 1)
                if len(ref_parts) == 2:
                    branch = ref_parts[1]

            available_updates.append(
                {
                    "ref": ref,
                    "name": name,
                    "version": version,
                    "branch": branch,
                    "commit": commit,
                }
            )

        return available_updates

    model_config = ConfigDict(extra="forbid")
