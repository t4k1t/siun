"""Test news command."""

import tempfile
from pathlib import Path
from unittest import mock

import feedparser
import pytest
from click.testing import CliRunner

from siun.cli import news
from siun.models import NewsProvider

DUMMY_FEED_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>PyPI recent updates for siun</title>
    <link>https://pypi.org/project/siun/</link>
    <description>Recent updates to the Python Package Index for siun</description>
    <language>en</language>    <item>
      <title>1.5.1</title>
      <link>https://pypi.org/project/siun/1.5.1/</link>
      <description>Report urgency of package upgrades</description>
<author>t4k1t+dev@protonmail.com</author>      <pubDate>Sat, 20 Sep 2025 18:09:49 GMT</pubDate>
    </item>    <item>
      <title>1.5.0</title>
      <link>https://pypi.org/project/siun/1.5.0/</link>
      <description>Report urgency of package upgrades</description>
<author>t4k1t+dev@protonmail.com</author>      <pubDate>Fri, 30 May 2025 12:58:56 GMT</pubDate>
    </item>    <item>
      <title>1.4.1</title>
      <link>https://pypi.org/project/siun/1.4.1/</link>
      <description>Report urgency of package upgrades</description>
<author>t4k1t+dev@protonmail.com</author>      <pubDate>Mon, 12 May 2025 18:06:28 GMT</pubDate>
    </item> </channel>
</rss>"""


class TestNewsCommand:
    """Test news command."""

    @pytest.mark.feature_news
    @pytest.mark.usefixtures("os_path_isfile_patch")
    @mock.patch("siun.cli_utils.get_config")
    @mock.patch("siun.cli._write_last_news_update")
    def test_news_command(self, mock_write_last_news_update, mock_get_config):
        """Test news CLI command with one source."""
        dummy_news_source = [mock.Mock(url="dummy-url", title=None, max_items=3)]
        dummy_config = mock.Mock()
        dummy_config.news = dummy_news_source
        with tempfile.TemporaryDirectory() as tmpdir:
            dummy_config.state_dir = Path(tmpdir)
            mock_get_config.return_value = dummy_config

            runner = CliRunner()
            # Let the library parse the dummy data so it can be substituted in the test call below
            parsed_feed = feedparser.parse(DUMMY_FEED_DATA)
            with mock.patch("siun.news.feedparser.parse", return_value=parsed_feed) as mock_feedparser_parse:
                result = runner.invoke(news, [])

                mock_feedparser_parse.assert_called_once()
                assert mock_feedparser_parse.call_args[0][0] == "dummy-url"
                assert result.exit_code == 0
                assert "PyPI recent updates for siun" in result.output
                # Titles
                assert "- 1.5.1" in result.output
                assert "- 1.5.0" in result.output
                assert "- 1.4.1" in result.output
                # Links
                assert "https://pypi.org/project/siun/1.5.1" in result.output
                assert "https://pypi.org/project/siun/1.5.0" in result.output
                assert "https://pypi.org/project/siun/1.4.1" in result.output
                # Publish dates
                assert "2025-09-20" in result.output
                assert "2025-05-30" in result.output
                assert "2025-05-12" in result.output

    @pytest.mark.feature_news
    @mock.patch("siun.cli_utils.get_config")
    def test_news_feature_not_installed(self, mock_get_config):
        """Test error when news feature is not installed."""
        dummy_config = mock.Mock()
        dummy_config.news = [mock.Mock(url="dummy-url", title=None, max_items=3)]
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch("siun.cli.INSTALLED_FEATURES", set()):
            dummy_config.state_dir = Path(tmpdir)
            mock_get_config.return_value = dummy_config

            runner = CliRunner()
            result = runner.invoke(news, [])
            assert result.exit_code != 0
            assert "news require the 'news' feature" in result.output

    @pytest.mark.feature_news
    @mock.patch("siun.cli_utils.get_config")
    def test_news_command_no_sources(self, mock_get_config):
        """Test news CLI command with no sources configured."""
        dummy_config = mock.Mock()
        dummy_config.news = []
        with tempfile.TemporaryDirectory() as tmpdir:
            dummy_config.state_dir = Path(tmpdir)
            mock_get_config.return_value = dummy_config

            runner = CliRunner()
            result = runner.invoke(news, [])

        assert result.exit_code == 0
        assert "No new entries" in result.output or result.output.strip() == ""

    @pytest.mark.feature_news
    @mock.patch("siun.cli_utils.get_config")
    def test_news_command_empty_feed(self, mock_get_config):
        """Test news CLI command with a feed that returns no entries."""
        dummy_news_source = [
            NewsProvider(
                url="/tmp/siun-tests/dummy-feed.xml",  # noqa: S108
                max_items=3,
                etag=None,
                last_modified=None,
            )
        ]
        dummy_config = mock.Mock()
        dummy_config.news = dummy_news_source
        dummy_config.state_dir = Path("/tmp/siun-tests")  # noqa: S108
        mock_get_config.return_value = dummy_config

        runner = CliRunner()
        parsed_feed = feedparser.parse(DUMMY_FEED_DATA)
        parsed_feed.feed = {"title": "Empty Feed"}
        parsed_feed.entries = []
        with mock.patch("siun.news.feedparser.parse", return_value=parsed_feed):
            result = runner.invoke(news, [])
            assert result.exit_code == 0
            assert "Empty Feed" in result.output
            assert "No new entries" in result.output

    @pytest.mark.feature_news
    @mock.patch("siun.cli_utils.get_config")
    @mock.patch("siun.cli._write_last_news_update")
    def test_news_command_nocolor(self, mock_write_last_news_update, mock_get_config):
        """Test news CLI command with --nocolor option."""
        dummy_news_source = [mock.Mock(url="dummy-url", title=None, max_items=1)]
        dummy_config = mock.Mock()
        dummy_config.news = dummy_news_source
        with tempfile.TemporaryDirectory() as tmpdir:
            dummy_config.state_dir = Path(tmpdir)
            mock_get_config.return_value = dummy_config

            runner = CliRunner()
            parsed_feed = feedparser.parse(DUMMY_FEED_DATA)
            with mock.patch("siun.news.feedparser.parse", return_value=parsed_feed):
                result = runner.invoke(news, ["--nocolor"])
                assert result.exit_code == 0
                # Should not contain ANSI color codes
                assert "\x1b[" not in result.output
                assert "PyPI recent updates for siun" in result.output


@pytest.fixture(autouse=True)
def os_path_isfile_patch(monkeypatch):
    """Patch os.path.isfile to always return True."""
    monkeypatch.setattr("os.path.isfile", lambda path: True)
