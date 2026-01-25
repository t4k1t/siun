"""Module for feeds and news."""

import calendar
import datetime

import feedparser

from siun.models import NewsEntry, NewsProvider

INSTALLED_FEATURES: set[str] = set()

try:
    import feedparser  # noqa: F401

    INSTALLED_FEATURES.add("news")
except ImportError:
    pass


def parse_feed_entries(source: NewsProvider) -> tuple[str, list[NewsEntry]]:
    """Parse feed entries from a news source."""
    # NOTE: feedparser seems to have some issues with type checking, hence the numerous pyright ignores
    parsed_feed = feedparser.parse(source.url, etag=source.etag, modified=source.last_modified)  # pyright: ignore[reportUnknownMemberType]
    # Update ETag and Last-Modified for future requests
    source._etag = getattr(parsed_feed, "etag", None)  # pyright: ignore[reportPrivateUsage]
    source._last_modified = getattr(parsed_feed, "modified", None)  # pyright: ignore[reportPrivateUsage]

    if not source.title:
        source.title = parsed_feed.feed.get("title", "No title")  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
    entries: list[NewsEntry] = []
    for entry in parsed_feed.entries[: source.max_items] or []:  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        entry_datetime = datetime.datetime.fromtimestamp(calendar.timegm(entry.published_parsed), tz=datetime.UTC)  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
        entries.append(
            NewsEntry(
                title=entry.get("title", "Untitled"),  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
                link=entry.get("link", ""),  # pyright: ignore[reportArgumentType, reportUnknownMemberType]
                published_at=entry_datetime.isoformat(),
            )
        )
    return source.title, entries  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
