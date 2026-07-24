"""Evaluate available updates against configured criteria and thresholds."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from siun.criteria import SiunCriterion
from siun.errors import CriterionError
from siun.models.criteria import V2Criterion
from siun.models.thresholds import V2Threshold

if TYPE_CHECKING:
    from siun.models.updates import PackageUpdate


class UpdateEvaluator:
    """Evaluate updates and determine matched criteria and threshold."""

    def evaluate(
        self,
        *,
        criteria_settings: list[V2Criterion],
        thresholds: list[V2Threshold],
        criteria: dict[str, SiunCriterion],
        available_updates: list[PackageUpdate] | None = None,
    ) -> tuple[dict[str, dict[str, Any]], V2Threshold | None]:
        """Evaluate updates and return matched criteria and current threshold match."""
        if available_updates is None:
            available_updates = []

        matched_criteria: dict[str, dict[str, Any]] = {}
        available_update_names = [update.name for update in available_updates]

        for criterion in criteria_settings:
            # If criterion has `0` weight we don't even have to check it.
            if criterion.weight == 0:
                continue

            try:
                user_criteria_settings = criterion.model_dump(exclude={"name", "short_name"})
                if criterion.name not in criteria:
                    message = (
                        f"Configured criterion '{criterion.name}' was not loaded. "
                        "Likely reasons:\n"
                        "- Missing or misplaced criterion file\n"
                        "- Criterion class missing or misnamed\n"
                        "- 'is_fulfilled' method not implemented\n"
                        "Check your criteria directory and configuration."
                    )
                    raise CriterionError(message, criterion.name)

                if criteria[criterion.name].is_fulfilled(user_criteria_settings, available_update_names):
                    matched_criteria[criterion.name] = user_criteria_settings

            except CriterionError:
                raise

            except Exception as error:
                criterion_settings = criterion.model_dump()
                message = f"Failed to evaluate criterion. Criterion settings: {criterion_settings}"
                raise CriterionError(message, criterion.name) from error

        score = sum(criterium["weight"] for criterium in matched_criteria.values())
        match = None
        for threshold in thresholds:
            if score >= threshold.score:
                match = threshold
                break

        return matched_criteria, match
