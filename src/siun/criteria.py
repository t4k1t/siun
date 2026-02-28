"""Criteria module."""

import re
from typing import Any


class SiunCriterion:
    """Base class for criteria."""

    def is_fulfilled(self, criteria_settings: dict[str, Any], available_updates: list[str]) -> bool:
        """Override me."""
        raise NotImplementedError


class CriterionAvailable(SiunCriterion):
    """Check if there are any available updates."""

    def is_fulfilled(self, criteria_settings: dict[str, Any], available_updates: list[str]) -> bool:
        """Check criterion."""
        return bool(available_updates)


class CriterionCount(SiunCriterion):
    """Check if count of available updates has exceeded threshold."""

    def is_fulfilled(self, criteria_settings: dict[str, Any], available_updates: list[str]) -> bool:
        """Check criterion."""
        is_exceeded: bool = len(available_updates) >= criteria_settings["count"]
        return is_exceeded


class CriterionPattern(SiunCriterion):
    """Check if list of available updates contains updates according to pattern."""

    def is_fulfilled(self, criteria_settings: dict[str, Any], available_updates: list[str]) -> bool:
        """Check criterion."""
        regex = re.compile(criteria_settings["pattern"])
        matches = list(filter(regex.match, available_updates))

        return bool(matches)
