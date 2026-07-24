"""Test update providers module."""

from unittest import mock

import pytest
from pydantic import ValidationError

from siun.errors import UpdateProviderError
from siun.models import PackageUpdate
from siun.providers import UpdateProvider, UpdateProviderFlatpak, UpdateProviderGeneric, UpdateProviderPacman


class TestUpdateProviderBase:
    """Test base interface for UpdateProviders."""

    def test_fetch_updates(self):
        """Test fetch_updates."""
        provider = UpdateProvider(name="dummy")
        with pytest.raises(NotImplementedError):
            provider.fetch_updates()

    def test_parse_updates(self):
        """Test parse_updates success."""
        provider = UpdateProvider(name="dummy")
        pattern = r"(?P<name>.+)"
        lines = ["package-x", "another package 1.2.3"]

        parsed_updates = provider.parse_updates(lines, pattern)
        names = [update.name for update in parsed_updates]
        assert "package-x" in names
        assert "another package 1.2.3" in names

    def test_parse_updates_empty(self):
        """Test parse_updates success if there are no updates."""
        provider = UpdateProvider(name="dummy")
        pattern = r"(?P<name>.+)"
        lines = []

        parsed_updates = provider.parse_updates(lines, pattern)
        assert parsed_updates == []

    def test_parse_updates_fails_on_no_matches(self):
        """Test parse_updates fails if output doesn't match pattern."""
        provider = UpdateProvider(name="dummy")
        pattern = r"(?P<name>a-z+)"
        lines = ["package-0", "package 1.2.3"]

        with pytest.raises(UpdateProviderError) as excinfo:
            provider.parse_updates(lines, pattern)
        assert "failed to parse output: package-0" in str(excinfo.value)


class TestUpdateProviderPacman:
    """Test UpdateProviderPacman."""

    @mock.patch("siun.providers.pacman.UpdateProviderPacman.pick_cmd", return_value=[":"])
    @mock.patch("subprocess.run")
    def test_fetch_updates(self, mock_run, mock_pick_cmd):
        """Test fetch_updates success."""
        mock_run.return_value = mock.Mock(stdout="siun 1.0.0 -> 2.0.0", returncode=0)
        provider = UpdateProviderPacman()
        available_updates = provider.fetch_updates()
        assert available_updates == [
            PackageUpdate(name="siun", old_version="1.0.0", new_version="2.0.0", provider="pacman")
        ]

    @mock.patch("siun.providers.pacman.UpdateProviderPacman.pick_cmd", return_value=[":"])
    @mock.patch("subprocess.run", side_effect=PermissionError("Permission denied"))
    def test_fetch_updates_cmd_fails(self, mock_run, mock_pick_cmd):
        """Test fetch_updates with failing cmd."""
        provider = UpdateProviderPacman()
        with pytest.raises(UpdateProviderError) as excinfo:
            provider.fetch_updates()
        assert "Permission denied" in str(excinfo.value)

    @mock.patch("siun.providers.pacman.UpdateProviderPacman.pick_cmd", return_value=[":"])
    def test_fetch_updates_cmd_not_found(self, fp):
        """Test fetch_updates with cmd not installed."""
        provider = UpdateProviderPacman()
        with pytest.raises(UpdateProviderError) as excinfo:
            provider.fetch_updates()
        assert "No such file or directory: ':'" in str(excinfo.value)

    def test_fetch_updates_invalid_cmd(self, fp):
        """Test fetch_updates with invalid cmd."""
        fp.register([":"], stdout="")

        with pytest.raises(ValidationError):
            UpdateProviderPacman(cmd="this_should_be_a_list.sh")


class TestUpdateProviderGeneric:
    """Test UpdateProviderGeneric."""

    def test_custom_pattern(self, fp):
        """Test parse_updates with custom pattern."""
        fp.register([":"], stdout="siun 2.7.18")

        provider = UpdateProviderGeneric(cmd=[":"], pattern=r"(?P<name>[a-z]+)\s+(?P<new_version>[0-9\.]+)")
        available_updates = provider.fetch_updates()
        assert available_updates == [
            PackageUpdate(name="siun", new_version="2.7.18", old_version=None, provider="generic")
        ]


class TestUpdateProviderFlatpak:
    """Test UpdateProviderFlatpak."""

    @mock.patch("siun.providers.flatpak.UpdateProviderFlatpak.pick_cmd")
    @mock.patch("subprocess.run")
    def test_fetch_updates_join_versions(self, mock_run, mock_pick_cmd):
        """Join installed and remote update versions by ref."""
        mock_pick_cmd.side_effect = [
            ["flatpak", "list", "--columns=ref,version"],
            ["flatpak", "remote-ls", "--updates", "--columns=ref,name,version,branch,commit"],
        ]
        mock_run.side_effect = [
            mock.Mock(stdout="app/org.gnome.App/x86_64/stable\t1.0\n", returncode=0),
            mock.Mock(stdout="app/org.gnome.App/x86_64/stable\tGNOME App\t1.1\tstable\tabcd\n", returncode=0),
        ]

        provider = UpdateProviderFlatpak()
        available_updates = provider.fetch_updates()

        assert available_updates == [
            PackageUpdate(name="GNOME App", old_version="1.0", new_version="1.1", provider="flatpak")
        ]

    @mock.patch("siun.providers.flatpak.UpdateProviderFlatpak.pick_cmd")
    @mock.patch("subprocess.run")
    def test_fetch_updates_missing_installed_entry(self, mock_run, mock_pick_cmd):
        """Allow updates without matching installed version rows."""
        mock_pick_cmd.side_effect = [
            ["flatpak", "list", "--columns=ref,version"],
            ["flatpak", "remote-ls", "--updates", "--columns=ref,name,version,branch,commit"],
        ]
        mock_run.side_effect = [
            mock.Mock(stdout="", returncode=0),
            mock.Mock(stdout="app/org.gnome.App/x86_64/stable\tGNOME App\t1.1\tstable\tabcd\n", returncode=0),
        ]

        provider = UpdateProviderFlatpak()
        available_updates = provider.fetch_updates()

        assert available_updates == [
            PackageUpdate(name="GNOME App", old_version=None, new_version="1.1", provider="flatpak")
        ]

    @mock.patch("siun.providers.flatpak.UpdateProviderFlatpak.pick_cmd")
    @mock.patch("subprocess.run")
    def test_fetch_updates_fallback_to_branch_or_commit(self, mock_run, mock_pick_cmd):
        """Fallback to branch or commit when remote version is missing."""
        mock_pick_cmd.side_effect = [
            ["flatpak", "list", "--columns=ref,version"],
            ["flatpak", "remote-ls", "--updates", "--columns=ref,name,version,branch,commit"],
        ]
        mock_run.side_effect = [
            mock.Mock(stdout="app/org.gnome.App/x86_64/stable\t1.0\n", returncode=0),
            mock.Mock(stdout="app/org.gnome.App/x86_64/stable\tGNOME App\t\tstable\tabcd\n", returncode=0),
        ]

        provider = UpdateProviderFlatpak()
        available_updates = provider.fetch_updates()

        assert available_updates == [
            PackageUpdate(name="GNOME App", old_version="1.0", new_version="stable", provider="flatpak")
        ]

    def test_parse_updates_fails_on_invalid_installed_row(self):
        """Raise on malformed flatpak list output."""
        provider = UpdateProviderFlatpak()

        with pytest.raises(UpdateProviderError) as excinfo:
            provider._parse_installed_versions(["b\t a\t d\t r\t o\t w\t"])

        assert "failed to parse output: b\t a\t d\t r\t o\t w\t" in str(excinfo.value)

    def test_parse_updates_fails_on_invalid_remote_row(self):
        """Raise on malformed flatpak remote-ls output."""
        provider = UpdateProviderFlatpak()

        with pytest.raises(UpdateProviderError) as excinfo:
            provider._parse_available_updates(["b\t a\t d\t r\t o\t w\t"])

        assert "failed to parse output: b\t a\t d\t r\t o\t w\t" in str(excinfo.value)

    def test_parse_installed_versions_accepts_ref_only_row(self):
        """Allow installed rows with ref and missing version."""
        provider = UpdateProviderFlatpak()

        installed_versions = provider._parse_installed_versions(["app/org.gnome.App/x86_64/stable"])

        assert installed_versions == {}

    def test_parse_available_updates_accepts_ref_only_row(self):
        """Allow remote rows with ref only and infer branch from ref."""
        provider = UpdateProviderFlatpak()

        available_updates = provider._parse_available_updates(
            ["org.freedesktop.Platform.codecs-extra/x86_64/25.08-extra"]
        )

        assert available_updates == [
            {
                "ref": "org.freedesktop.Platform.codecs-extra/x86_64/25.08-extra",
                "name": "",
                "version": "",
                "branch": "25.08-extra",
                "commit": "",
            }
        ]
