"""Module for models related to news feeds."""

from __future__ import annotations

from pydantic import BaseModel, computed_field


class NewsProvider(BaseModel):
    """Struct for news sources."""

    url: str
    title: str = ""
    max_items: int = 3
    _etag: str | None = None
    _last_modified: str | None = None

    @computed_field
    @property
    def etag(self) -> str | None:
        """Get ETag if available."""
        if getattr(self, "_etag", False):
            return self._etag

        return None

    @computed_field
    @property
    def last_modified(self) -> str | None:
        """Get last_modified if available."""
        if getattr(self, "_last_modified", False):
            return self._last_modified

        return None


class NewsEntry(BaseModel):
    """Struct for news entries."""

    title: str
    link: str
    published_at: str
