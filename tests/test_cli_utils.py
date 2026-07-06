"""Test CLI utils helpers."""

from pathlib import Path
from unittest import mock

import pytest

from siun.cli_utils import _extract_distro_candidates, guess_update_providers
from siun.errors import UpdateProviderError


class TestGuessUpdateProviders:
    """Test distro based provider guessing."""

    @mock.patch("siun.cli_utils._get_os_release_content", return_value='ID="arch"\n')
    def test_guess_from_id(self, mock_get_os_release_content):
        """Prefer distro ID when mapped."""
        providers = guess_update_providers()

        assert [provider.name for provider in providers] == ["aur", "pacman"]
        assert mock_get_os_release_content.call_count == 1

    @mock.patch("siun.cli_utils._get_os_release_content", return_value="ID=foo\nID_LIKE=arch\n")
    def test_guess_from_id_like(self, mock_get_os_release_content):
        """Fall back to ID_LIKE when ID is unknown."""
        providers = guess_update_providers()

        assert [provider.name for provider in providers] == ["aur", "pacman"]
        assert mock_get_os_release_content.call_count == 1

    @mock.patch("siun.cli_utils._get_os_release_content", return_value="ID=rhel\nID_LIKE=arch\n")
    def test_guess_with_alias(self, mock_get_os_release_content):
        """Use ID_LIKE when ID maps to no providers."""
        providers = guess_update_providers()

        assert [provider.name for provider in providers] == ["aur", "pacman"]
        assert mock_get_os_release_content.call_count == 1

    @mock.patch("siun.cli_utils._get_os_release_content", return_value="ID=manjaro\nID_LIKE=debian\n")
    def test_id_has_precedence_over_id_like(self, mock_get_os_release_content):
        """Prefer ID when it resolves to providers."""
        providers = guess_update_providers()

        assert [provider.name for provider in providers] == ["aur", "pacman"]
        assert mock_get_os_release_content.call_count == 1

    @mock.patch("siun.cli_utils._get_os_release_content", side_effect=["NAME=Unknown\n", "ID=arch\n"])
    def test_falls_back_to_second_release_file(self, mock_get_os_release_content):
        """Try system-release after os-release when needed."""
        providers = guess_update_providers()

        assert [provider.name for provider in providers] == ["aur", "pacman"]
        assert mock_get_os_release_content.call_count == 2
        called_paths = [call.args[0] for call in mock_get_os_release_content.call_args_list]
        assert called_paths == [Path("/etc/os-release"), Path("/etc/system-release")]

    @mock.patch("siun.providers.base.which", return_value=None)
    @mock.patch("siun.cli_utils._get_os_release_content", return_value='ID="arch"\n')
    def test_guess_returns_providers_even_if_commands_are_unavailable(self, mock_get_os_release_content, mock_which):
        """Return providers even if their commands are missing."""
        providers = guess_update_providers()

        assert [provider.name for provider in providers] == ["aur", "pacman"]
        assert mock_get_os_release_content.call_count == 1

        for provider in providers:
            with pytest.raises(UpdateProviderError, match="no suitable command found"):
                provider.fetch_updates()

        assert mock_which.call_count > 0


class TestOsReleaseParsing:
    """Test os-release content parsing."""

    def test_extract_distro_candidates(self):
        """Parse ID and ID_LIKE values in order."""
        content = """
        NAME="Fedora Linux"
        ID=fedora
        ID_LIKE="rhel centos"
        """

        assert _extract_distro_candidates(content) == ["fedora", "rhel", "centos"]

    def test_extract_distro_candidates_ignores_invalid_lines(self):
        """Ignore comments, malformed lines, and duplicates."""
        content = """
        # comment
        SOMETHING
        ID="ubuntu"
        ID_LIKE='debian ubuntu'
        """

        assert _extract_distro_candidates(content) == ["ubuntu", "debian"]
