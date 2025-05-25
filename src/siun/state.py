"""Internal state of siun and available updates."""

import datetime
import importlib.util
import shutil
import tempfile
from enum import Enum
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from siun.criteria import CriterionAvailable, CriterionCount, CriterionCritical, SiunCriterion
from siun.errors import CriterionError
from siun.util import get_default_criteria_dir

BUILTIN_CRITERIA = {
    "available": CriterionAvailable(),
    "count": CriterionCount(),
    "critical": CriterionCritical(),
}
EXPECTED_CLASS = "SiunCriterion"


def _load_user_criteria(*, criteria_settings: dict[str, Any], include_path: Path | None = None) -> dict[str, Any]:
    """Load user criteria."""
    user_criteria: dict[str, SiunCriterion] = {}
    enabled_criteria: list[str] = []
    if not include_path:
        include_path = get_default_criteria_dir()

    if not include_path.exists() or not include_path.is_dir():
        return user_criteria

    # Get list of enabled user criteria from config
    for setting, value in criteria_settings.items():
        if "_weight" in setting and value > 0:
            enabled_criteria.append(setting.split("_weight")[0])

    for f_name in include_path.iterdir():
        # Only load enabled user criteria
        if f_name.suffix != ".py" or f_name.stem not in enabled_criteria:
            continue
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


class SortableEnum(Enum):
    """Sortable Enum subclass."""

    def __le__(self, other: Any):
        """Make enum sortable: Less Than or Equal."""
        if self.__class__ is other.__class__:
            if self == other:
                return True
            return self.__lt__(other)
        return NotImplemented

    def __lt__(self, other: Any):
        """Make enum sortable: Less Than."""
        if self.__class__ is other.__class__:
            return list(self.__class__).index(self) < list(self.__class__).index(other)
        return NotImplemented


class Threshold(SortableEnum):
    """Threshold levels."""

    available = "available"
    warning = "warning"
    critical = "critical"


class State(SortableEnum):
    """Define update state."""

    UNKNOWN = "UNKNOWN"
    OK = "OK"
    AVAILABLE_UPDATES = "AVAILABLE_UPDATES"
    WARNING_UPDATES = "WARNING_UPDATES"
    CRITICAL_UPDATES = "CRITICAL_UPDATES"


class StateText(Enum):
    """Translate state to text representation."""

    OK = "Ok"
    AVAILABLE_UPDATES = "Updates available"
    WARNING_UPDATES = "Updates recommended"
    CRITICAL_UPDATES = "Updates required"
    UNKNOWN = "Unknown"


class StateColor(Enum):
    """Translate state to color."""

    OK = "green"
    AVAILABLE_UPDATES = "blue"
    WARNING_UPDATES = "yellow"
    CRITICAL_UPDATES = "red"
    UNKNOWN = "magenta"


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

    criteria_settings: dict[str, Any] = {}
    thresholds_settings: dict[str, int] = {}
    thresholds: dict[int, str] = {}
    available_updates: list[str] = []
    matched_criteria: dict[str, dict[str, Any]] = {}
    state: State = State.UNKNOWN
    last_state: State = State.UNKNOWN
    last_update: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)

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
    def color(self) -> StateColor:
        """Get color based on state."""
        return getattr(StateColor, self.state.name)

    @property
    def text_value(self) -> StateText:
        """Get text value based on state."""
        return getattr(StateText, self.state.name)

    @property
    def format_object(self) -> FormatObject:
        """Provide prepared values for formatters."""
        return FormatObject(
            available_updates=", ".join(self.available_updates),
            last_update=self.last_update.replace(microsecond=0).isoformat(),
            matched_criteria=", ".join(self.matched_criteria.keys()),
            matched_criteria_short=",".join([match[:2] for match in self.matched_criteria]),
            score=self.score,
            status_text=self.text_value.value,
            update_count=self.count,
            state_color=self.color.value,
            state_name=self.text_value.name,
        )

    def update(self, available_updates: list[str] | None = None) -> None:
        """Update state of updates."""
        self.touch()
        if available_updates is None:
            available_updates = []

        self.available_updates = available_updates

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
        for name, criterion in criteria.items():
            if self.criteria_settings[f"{name}_weight"] <= 0:
                continue  # Skip criteria with non-positive weight
            try:
                if criterion.is_fulfilled(self.criteria_settings, available_updates):
                    self.matched_criteria[name] = {"weight": self.criteria_settings[f"{name}_weight"]}
            except Exception as error:
                message = str(error)
                raise CriterionError(message, name) from error

        thresholds = {
            threshold: State(f"{name.upper()}_UPDATES").name for name, threshold in self.thresholds_settings.items()
        }
        self.thresholds = thresholds

        reversed_thresholds = reversed(self.thresholds.keys())
        for threshold in reversed_thresholds:
            if self.score >= threshold:
                self.state = State(self.thresholds[threshold])
                break
            self.state = State("OK")

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
            update_file.write(self.model_dump_json())
            update_file.flush()
            shutil.copy(update_file.name, state_file_path)


def load_state(state_file_path: Path) -> Updates | None:
    """Read state from disk."""

    def is_pytype_error(err_input: Any):
        if not isinstance(err_input, dict):
            return False
        if "py-type" in err_input:
            return True

    if not state_file_path.exists():
        return None

    with Path.open(state_file_path) as update_file:
        try:
            return Updates.model_validate_json(update_file.read())
        except ValidationError as error:
            # Handle state file from siun<=1.3.0
            pytype_errors = [is_pytype_error(err.get("input")) for err in error.errors()]
            if all(pytype_errors):
                # Treat state as unknown, it'll get fixed automatically next time a write occurs
                return None
            else:
                # Raise normally if anything else is wrong with the state file
                raise error
