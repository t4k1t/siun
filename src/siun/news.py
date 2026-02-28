"""Module for feeds and news."""

import calendar
import datetime

from siun.models import NewsEntry, NewsProvider

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
