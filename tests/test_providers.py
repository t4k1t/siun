"""Test update providers module."""

import pytest
from pydantic import ValidationError

from siun.errors import UpdateProviderError
from siun.models import PackageUpdate
from siun.providers import UpdateProvider, UpdateProviderGeneric, UpdateProviderPacman


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

    def test_fetch_updates(self, fp):
        """Test fetch_updates success."""
        fp.register([":"], stdout="siun 1.0.0 -> 2.0.0")

        provider = UpdateProviderPacman(cmd=[":"])
        available_updates = provider.fetch_updates()
        assert available_updates == [PackageUpdate(name="siun", old_version="1.0.0", new_version="2.0.0")]

    def test_fetch_updates_cmd_fails(self, fp):
        """Test fetch_updates with failing cmd."""

        def callback_func(process):
            process.returncode = 2
            raise PermissionError("Permission denied")  # noqa: EM101

        fp.register([":"], callback=callback_func)

        provider = UpdateProviderPacman(cmd=[":"])
        with pytest.raises(UpdateProviderError) as excinfo:
            provider.fetch_updates()
        assert "Permission denied" in str(excinfo.value)

    def test_fetch_updates_cmd_not_found(self, fp):
        """Test fetch_updates with cmd not found."""

        def callback_func(process):
            process.returncode = 2
            raise FileNotFoundError("command not found")  # noqa: EM101

        fp.register([":"], callback=callback_func)

        provider = UpdateProviderPacman(cmd=[":"])
        with pytest.raises(UpdateProviderError) as excinfo:
            provider.fetch_updates()
        assert "command not found" in str(excinfo.value)

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
        assert available_updates == [PackageUpdate(name="siun", new_version="2.7.18", old_version=None)]
