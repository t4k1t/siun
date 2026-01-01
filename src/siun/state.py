"""Internal state of siun and available updates."""

import datetime
import importlib.util
import shutil
import tempfile
import traceback
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from siun.criteria import CriterionAvailable, CriterionCount, CriterionPattern, SiunCriterion
from siun.errors import (
    CmdRunError,
    CriterionError,
    SiunStateUpdateError,
)
from siun.models import ClickColor, PackageUpdate, V2Criterion, V2Threshold
from siun.providers import UpdateProvider
from siun.util import get_default_criteria_dir

BUILTIN_CRITERIA = {
    "available": CriterionAvailable(),
    "count": CriterionCount(),
    "pattern": CriterionPattern(),
}
EXPECTED_CLASS = "SiunCriterion"


def _load_user_criteria(*, criteria_settings: list[V2Criterion], include_path: Path | None = None) -> dict[str, Any]:
    """Load user criteria."""
    # TODO: Improved error handling
    # TODO: Only load from trusted dir, unless validated (how to validate? permisissions? what else?)
    # TODO: Try running code in subprocess with restricted permissions
    # TODO: Document risks
    user_criteria: dict[str, SiunCriterion] = {}
    if not include_path:
        include_path = get_default_criteria_dir()

    if not include_path.exists() or not include_path.is_dir():
        return user_criteria

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
            class_inst = py_mod.SiunCriterion()
            user_criteria[file_path.stem] = class_inst

    return user_criteria


class FormatObject(BaseModel):
    """Objects for output formatting."""

    available_updates: str
    last_update: str
    matched_criteria: str
    matched_criteria_short: str
    score: int
    status_text: str
    update_count: int
    # Excluded fields won't be usable in custom format
    state_color: str = Field(exclude=True)
    state_name: str = Field(exclude=True)


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
            user_criteria = _load_user_criteria(criteria_settings=self.criteria_settings)
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
        """
        Write state to disk.

        Avoids partially written state file (and therefore invalid JSON) by
        creating a temporary file first and only replacing the state file once
        the writing operation is done.
        """
        if not Path.exists(state_file_path.parent):
            # Create parent dir for state file path if it doesn't exist
            Path.mkdir(Path(state_file_path.parent))
        with tempfile.NamedTemporaryFile(mode="w+") as update_file:
            update_file.write(
                self.model_dump_json(exclude={"thresholds", "last_match", "matched_criteria", "criteria_settings"})
            )
            update_file.flush()
            shutil.copy(update_file.name, state_file_path)


def load_state(state_file_path: Path) -> Updates | None:
    """Read state from disk."""
    if not state_file_path.exists():
        return None

    with Path.open(state_file_path) as update_file:
        return Updates.model_validate_json(update_file.read())


def update_state_with_available_packages(siun_state: Updates, update_provider: UpdateProvider) -> None:
    """Fetch available package updates and (re-)evaluate update state."""
    try:
        siun_state.evaluate(available_updates=update_provider.fetch_updates())
    except CmdRunError as error:
        message = f"failed to query available updates: {error}"
        raise SiunStateUpdateError(message) from error
    except CriterionError as error:
        message = f"failed to check criterion [{error.criterion_name}]: {error.message}"
        raise SiunStateUpdateError(message) from error
