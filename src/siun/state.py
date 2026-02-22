"""Internal state of siun and available updates."""

import datetime
import importlib.util
import traceback
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from siun.criteria import CriterionAvailable, CriterionCount, CriterionPattern, SiunCriterion
from siun.errors import (
    CriterionError,
    SiunStateUpdateError,
    UpdateProviderError,
)
from siun.models import ClickColor, FormatObject, PackageUpdate, V2Criterion, V2Threshold
from siun.providers import UpdateProvider
from siun.util import get_default_criteria_dir, is_path_world_writable, safely_write_to_disk

BUILTIN_CRITERIA = {
    "available": CriterionAvailable(),
    "count": CriterionCount(),
    "pattern": CriterionPattern(),
}
EXPECTED_CLASS = "SiunCriterion"


def load_user_criteria(*, criteria_settings: list[V2Criterion], include_path: Path | None = None) -> dict[str, Any]:
    """Load user criteria."""
    user_criteria: dict[str, SiunCriterion] = {}
    if not include_path:
        include_path = get_default_criteria_dir()

    if not include_path.exists() or not include_path.is_dir():
        return user_criteria

    if is_path_world_writable(include_path):
        message = (
            f"Criteria directory '{include_path}' is world-writable. "
            "Please change its permissions to be more restrictive."
        )
        raise ImportError(message)

    # Get list of enabled user criteria from config
    enabled_criteria = {criterion.name for criterion in criteria_settings if criterion.weight != 0}

    for f_name in include_path.iterdir():
        # Only load enabled user criteria
        if f_name.suffix != ".py" or f_name.stem not in enabled_criteria:
            continue  # Skip non-Python files
        file_path = include_path / f_name
        py_mod_loader = SourceFileLoader(file_path.stem, file_path.as_posix())
        py_mod_spec = importlib.util.spec_from_loader(py_mod_loader.name, py_mod_loader)
        if py_mod_spec is None:
            message = "Could not create module specification for source file loader"
            raise ImportError(message)
        py_mod = importlib.util.module_from_spec(py_mod_spec)
        py_mod_loader.exec_module(py_mod)
        if hasattr(py_mod, EXPECTED_CLASS):
            class_obj = getattr(py_mod, EXPECTED_CLASS)
            # Check inheritance
            if not hasattr(class_obj, "is_fulfilled") or not callable(class_obj.is_fulfilled):
                continue  # An error is raised later if any configured criteria could not be loaded
            class_inst = py_mod.SiunCriterion()
            user_criteria[file_path.stem] = class_inst

    return user_criteria


# TODO: Move to models; Problem: `Updates` is not fully defined; you should
#       define `V2Criterion`, then call `Updates.model_rebuild()`
class Updates(BaseModel):
    """Internale state struct."""

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

    def evaluate(self, available_updates: list[PackageUpdate] | None = None) -> None:
        """Update state of updates."""
        self.touch()
        if available_updates is None:
            available_updates = []

        self.available_updates = available_updates
        self.matched_criteria = {}  # Reset matches

        # Load criteria
        criteria = BUILTIN_CRITERIA
        user_criteria = {}
        try:
            user_criteria = load_user_criteria(criteria_settings=self.criteria_settings)
        except Exception as error:
            message = f"unable to load user criteria: {error}"
            raise CriterionError(message, None) from error
        # NOTE: It's possible to overload builtin criteria this way
        criteria.update(user_criteria)

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
                    raise CriterionError(message, crit.name)
                if criteria[crit.name].is_fulfilled(
                    user_criteria_settings, [update.name for update in available_updates]
                ):
                    self.matched_criteria[crit.name] = user_criteria_settings
            except CriterionError as error:
                raise error
            except Exception as error:
                crit_settings = crit.model_dump()
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
        return safely_write_to_disk(
            content=self.model_dump_json(exclude={"thresholds", "last_match", "matched_criteria", "criteria_settings"}),
            target_path=state_file_path,
        )


def load_state(state_file_path: Path) -> Updates | None:
    """Read state from disk."""
    if not state_file_path.exists():
        return None

    with Path.open(state_file_path) as update_file:
        return Updates.model_validate_json(update_file.read())


def get_package_updates(update_providers: list[UpdateProvider]) -> list[PackageUpdate]:
    """Fetch available package updates."""
    package_updates: list[PackageUpdate] = []
    for provider in update_providers:
        package_updates.extend(provider.fetch_updates())

    return package_updates


def update_state_with_available_packages(siun_state: Updates, update_providers: list[UpdateProvider]) -> None:
    """Fetch available package updates and (re-)evaluate update state."""
    try:
        siun_state.evaluate(available_updates=get_package_updates(update_providers))
    except UpdateProviderError as error:
        message = f"failed to query available updates: {error}"
        raise SiunStateUpdateError(message) from error
    except CriterionError as error:
        message = f"failed to check criterion [{error.criterion_name}]: {error.message}"
        raise SiunStateUpdateError(message) from error
