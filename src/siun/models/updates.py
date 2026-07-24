"""Models dealing with package updates."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from siun.criteria import SiunCriterion
from siun.models.criteria import V2Criterion
from siun.models.formatting import ClickColor, FormatObject
from siun.models.thresholds import V2Threshold
from siun.update_evaluator import UpdateEvaluator


class PackageUpdate(BaseModel):
    """Struct representing an available update."""

    name: str
    old_version: str | None = None
    new_version: str | None = None
    provider: str

    model_config = ConfigDict(extra="allow")


class Updates(BaseModel):
    """Internal state struct."""

    criteria_settings: list[V2Criterion] = []
    thresholds: list[V2Threshold] = []
    available_updates: list[PackageUpdate] = []
    matched_criteria: dict[str, dict[str, Any]] = {}
    last_update: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)
    match: V2Threshold | None = None
    last_match: V2Threshold | None = None

    def touch(self) -> None:
        """Set last_update to now."""
        self.last_update = datetime.datetime.now(tz=datetime.UTC)

    @property
    def score(self) -> int:
        """Calculate score from criteria weights."""
        return sum([criterium["weight"] for criterium in self.matched_criteria.values()])

    @property
    def count(self) -> int:
        """Get count of available updates."""
        return len(self.available_updates)

    @property
    def color(self) -> ClickColor:
        """Get color of matched threshold."""
        if not self.match:
            return ClickColor.reset
        return self.match.color

    @property
    def text_value(self) -> str:
        """Get text value of matched threshold."""
        if not self.match:
            return "No matches."
        return self.match.text

    @property
    def format_object(self) -> FormatObject:
        """Provide prepared values for formatters."""
        return FormatObject(
            available_updates=", ".join([update.name for update in self.available_updates]),
            last_update=self.last_update.replace(microsecond=0).isoformat(),
            matched_criteria=", ".join(self.matched_criteria.keys()),
            matched_criteria_short=",".join([match["name_short"] for match in self.matched_criteria.values()]),
            score=self.score,
            status_text=self.text_value,
            update_count=self.count,
            state_color=self.color.value,
            state_name=self.text_value,
        )

    def evaluate(
        self,
        criteria: dict[str, SiunCriterion],
        available_updates: list[PackageUpdate] | None = None,
    ) -> None:
        """Update state of updates. Criteria must be passed in."""
        self.touch()
        if available_updates is None:
            available_updates = []

        self.available_updates = available_updates
        evaluator = UpdateEvaluator()
        self.matched_criteria, self.match = evaluator.evaluate(
            criteria_settings=self.criteria_settings,
            thresholds=self.thresholds,
            criteria=criteria,
            available_updates=available_updates,
        )

    def persist_state(self, state_file_path: Path) -> None:
        """Write state to disk."""
        from siun.util import safely_write_to_disk

        return safely_write_to_disk(
            content=self.model_dump_json(exclude={"thresholds", "last_match", "matched_criteria", "criteria_settings"}),
            target_path=state_file_path,
        )
