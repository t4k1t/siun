"""Module for feeds and news."""

import calendar
import datetime
import json
from pathlib import Path

import click

from siun.errors import (
    SiunCLIError,
)
from siun.models import ClickColor, NewsEntry, NewsProvider
from siun.util import safely_write_to_disk

INSTALLED_FEATURES: set[str] = set()

try:
    import feedparser  # noqa: F401

    INSTALLED_FEATURES.add("news")
except ImportError:
    pass


def parse_feed_entries(source: NewsProvider) -> tuple[str, list[NewsEntry]]:
    """Parse feed entries from a news source."""
    parsed_feed = feedparser.parse(source.url, etag=source.etag, modified=source.last_modified)
    # Update ETag and Last-Modified for future requests
    source._etag = getattr(parsed_feed, "etag", None)
    source._last_modified = getattr(parsed_feed, "modified", None)

    if not source.title:
        source.title = parsed_feed.feed.get("title", "No title")
    entries: list[NewsEntry] = []
    for entry in parsed_feed.entries[: source.max_items] or []:
        entry_datetime = datetime.datetime.fromtimestamp(calendar.timegm(entry.published_parsed), tz=datetime.UTC)
        entries.append(
            NewsEntry(
                title=entry.get("title", "Untitled"),
                link=entry.get("link", ""),
                published_at=entry_datetime.isoformat(),
            )
        )
    return source.title, entries


def load_news_state(sources: list[NewsProvider], last_update_path: Path) -> None:
    """Load ETag and Last-Modified headers from disk for news sources."""
    from_disk: list[dict[str, str]] = []
    if last_update_path.exists() and last_update_path.is_file():
        with last_update_path.open("r", encoding="utf-8") as file_obj:
            try:
                from_disk = json.loads(file_obj.read())
            except json.JSONDecodeError as error:
                raise SiunCLIError(
                    message=f"Failed to parse last news update state from disk; state path: {last_update_path}"
                ) from error

    for source in sources:
        for saved_source in from_disk:
            if source.url == saved_source.get("url", ""):
                source._etag = saved_source.get("etag", None)
                source._last_modified = saved_source.get("last_modified", None)
                if not source.title:
                    source.title = saved_source.get("title", "No title")
                break


def save_news_state(sources: list[NewsProvider], last_update_path: Path) -> None:
    """Write news state to disk."""
    return safely_write_to_disk(
        content=json.dumps(
            [source.model_dump(include={"url", "etag", "last_modified", "title"}) for source in sources]
        ),
        target_path=last_update_path,
    )


def format_news_entries(news_entries: dict[str, list[NewsEntry]], nocolor: bool) -> str:
    """Format news entries for output."""
    output = []
    for feed_title, entries in news_entries.items():
        output.append(click.style(f"{feed_title}:\n", fg=ClickColor.yellow.value if not nocolor else None))
        for entry in entries:
            output.append(f"- {entry.title}")
            output.append(click.style(f"  {entry.link}", fg=ClickColor.blue.value if not nocolor else None))
            output.append(f"  {entry.published_at}\n")
        if not entries:
            output.append("No new entries.\n")
    return "\n".join(output)
