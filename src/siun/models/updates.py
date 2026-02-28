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
        self.matched_criteria = {}  # Reset matches

        # Check criteria
        for crit in self.criteria_settings:
            if crit and crit.weight == 0:
                continue  # Skip criteria with weight 0
            try:
                user_criteria_settings = crit.model_dump(exclude={"name", "short_name"})
                if crit.name not in criteria:
                    message = (
                        f"Configured criterion '{crit.name}' was not loaded. "
                        "Likely reasons:\n"
                        "- Missing or misplaced criterion file\n"
                        "- Criterion class missing or misnamed\n"
                        "- 'is_fulfilled' method not implemented\n"
                        "Check your criteria directory and configuration."
                    )
                    from siun.errors import CriterionError

                    raise CriterionError(message, crit.name)
                if criteria[crit.name].is_fulfilled(
                    user_criteria_settings, [update.name for update in available_updates]
                ):
                    self.matched_criteria[crit.name] = user_criteria_settings
            except Exception as error:
                from siun.errors import CriterionError

                crit_settings = crit.model_dump()
                import traceback

                tb = traceback.format_exc()
                message = f"Criterion settings: {crit_settings}\nTraceback:\n{tb}"
                raise CriterionError(message, crit.name) from error

        for threshold in self.thresholds:
            if self.score >= threshold.score:
                self.match = threshold
                break
        else:
            # Reset match if no thresholds matched
            self.match = None

    def persist_state(self, state_file_path: Path) -> None:
        """Write state to disk."""
        from siun.util import safely_write_to_disk

        return safely_write_to_disk(
            content=self.model_dump_json(exclude={"thresholds", "last_match", "matched_criteria", "criteria_settings"}),
            target_path=state_file_path,
        )
