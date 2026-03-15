"""Module for checking for updates and evaluating criteria."""

import datetime
from pathlib import Path

from siun.errors import (
    SiunGetUpdatesError,
    SiunStateUpdateError,
)
from siun.models import V2Criterion, V2Threshold
from siun.models.updates import Updates
from siun.providers import UpdateProvider
from siun.state import get_merged_criteria, get_package_updates, load_state


def _is_cache_stale(existing_state, now, min_age):
    return existing_state and existing_state.last_update < (now - min_age)


def _evaluate_state(state, criteria_dict, updates):
    try:
        state.evaluate(criteria_dict, available_updates=updates)
    except SiunStateUpdateError as error:
        raise SiunGetUpdatesError(error.message) from error


def _persist_state(state, path):
    try:
        state.persist_state(path)
    except Exception as error:
        message = f"failed to write state to disk: {error}"
        raise SiunGetUpdatesError(message) from error


def get_updates(
    *,
    no_cache: bool,
    no_update: bool,
    criteria: list[V2Criterion],
    thresholds: list[V2Threshold],
    cache_min_age_minutes: int,
    state_file_path: Path,
    update_providers: list[UpdateProvider],
) -> Updates:
    """Get available updates and evaluate criteria."""
    now = datetime.datetime.now(tz=datetime.UTC)
    cache_min_age = datetime.timedelta(minutes=cache_min_age_minutes)
    criteria_dict = get_merged_criteria(criteria_settings=criteria)

    if no_cache:
        state = Updates(criteria_settings=criteria, thresholds=thresholds)
        if no_update:
            return state
        _evaluate_state(state, criteria_dict, get_package_updates(update_providers))
        return state

    try:
        existing_state = load_state(state_file_path)
    except Exception as error:
        message = f"failed to load state from disk: {error}"
        raise SiunGetUpdatesError(message) from error

    should_update_cache = not existing_state or _is_cache_stale(existing_state, now, cache_min_age)
    needs_update = False

    if existing_state:
        state = existing_state
        state.last_match = state.match
        state.thresholds = thresholds
        state.criteria_settings = criteria
        _evaluate_state(state, criteria_dict, existing_state.available_updates)
        if state.last_match != state.match:
            needs_update = True
    else:
        state = Updates(criteria_settings=criteria, thresholds=thresholds)

    if no_update:
        return state

    if should_update_cache:
        _evaluate_state(state, criteria_dict, get_package_updates(update_providers))
        _persist_state(state, state_file_path)
    elif needs_update:
        _persist_state(state, state_file_path)

    return state
