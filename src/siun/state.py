"""Internal state of siun and available updates."""

import datetime
import importlib.util
import json
import shutil
import tempfile
from enum import Enum
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any, no_type_check

from pydantic import BaseModel, Field

from siun.config import Threshold
from siun.criteria import CriterionAvailable, CriterionCount, CriterionCritical, SiunCriterion
from siun.errors import CriterionError

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
        include_path = Path().home() / ".config" / "siun" / "criteria"

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
        py_mod = importlib.util.module_from_spec(py_mod_spec)
        py_mod_loader.exec_module(py_mod)
        if hasattr(py_mod, EXPECTED_CLASS):
            class_inst = py_mod.SiunCriterion()
            user_criteria[file_path.stem] = class_inst

    return user_criteria


class State(Enum):
    """Define update state."""

    OK = "OK"
    AVAILABLE_UPDATES = "AVAILABLE_UPDATES"
    WARNING_UPDATES = "WARNING_UPDATES"
    CRITICAL_UPDATES = "CRITICAL_UPDATES"
    UNKNOWN = "UNKNOWN"


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


class SiunState(BaseModel):
    """Internal state struct."""

    criteria_settings: dict[str, Any]
    thresholds: dict[int, str]
    available_updates: list[str]
    matched_criteria: dict[str, dict[str, Any]]
    state: State
    last_update: datetime.datetime


class FormatObject(BaseModel):
    """Objects for custom output formatting."""

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


class StateEncoder(json.JSONEncoder):
    """Custom state encoder.

    Serializes Enum and datetime types to JSON.
    """

    @no_type_check
    def default(self, o):
        """Override to support more types."""
        if isinstance(o, Enum):
            return {"py-type": type(o).__name__, "value": o.value}
        if isinstance(o, datetime.datetime):
            return {"py-type": type(o).__name__, "value": o.isoformat()}

        return json.JSONEncoder.default(self, o)


class StateDecoder(json.JSONDecoder):
    """Custom state decoder.

    Deserialize custom python types from JSON.
    """

    @no_type_check
    def __init__(self, *args, **kwargs):  # noqa: D107
        json.JSONDecoder.__init__(self, *args, **kwargs, object_hook=self._custom_object_hook)

    @no_type_check
    def _custom_object_hook(self, o):
        pytype = o.get("py-type")
        if not pytype:
            return o

        if pytype == "datetime":
            return datetime.datetime.fromisoformat(o["value"])
        elif pytype in [StateText.__name__, StateColor.__name__, State.__name__]:
            t = globals()[pytype]
            return t(o["value"])
        else:
            raise NotImplementedError


class Updates:
    """Handle available updates."""

    def __init__(
        self,
        *,
        criteria_settings: dict[str, Any],
        thresholds_settings: dict[Threshold, int],
        available_updates: list[str] | None = None,
        matched_criteria: dict[str, dict[str, Any]] | None = None,
        state: State | None = None,
        last_update: datetime.datetime | None = None,
        thresholds: dict[int, str] | None = None,
    ):
        self.criteria_settings = criteria_settings
        if thresholds is None:
            thresholds = {
                threshold: State(f"{name.value.upper()}_UPDATES").name
                for name, threshold in thresholds_settings.items()
            }
        self.thresholds = thresholds

        if available_updates is None:
            available_updates = []
        self.available_updates = available_updates
        if matched_criteria is None:
            matched_criteria = {}
        self.matched_criteria = matched_criteria
        if state is None:
            state = State.UNKNOWN
        self.state = state
        if last_update is None:
            last_update = datetime.datetime.now(tz=datetime.UTC)
        self.last_update = last_update

    def _track_update(self) -> None:
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
        self._track_update()
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

        thresholds = reversed(self.thresholds.keys())
        for threshold in thresholds:
            if self.score >= threshold:
                self.state = State(self.thresholds[threshold])
                break
            self.state = State("OK")

    def persist_state(self, update_file_path: Path | None = None) -> None:
        """Write state to disk.

        Avoids partially written state file (and therefore invalid JSON) by
        creating a temporary file first and only replacing the state file once
        the writing operation is done.
        """
        tempdir = tempfile.gettempdir()
        if not update_file_path:
            update_file_path = Path("/".join([tempdir, "siun-state.json"]))
        with tempfile.NamedTemporaryFile(mode="w+") as update_file:
            json.dump(self.__dict__, update_file, cls=StateEncoder)
            update_file.flush()
            shutil.copy(update_file.name, update_file_path)

    @classmethod
    def read_state(cls, update_file_path: Path | None = None) -> SiunState | None:
        """Read state from disk."""
        tempdir = tempfile.gettempdir()
        if not update_file_path:
            update_file_path = Path("/".join([tempdir, "siun-state.json"]))
        if not update_file_path.exists():
            return None

        with Path.open(update_file_path) as update_file:
            return SiunState(**json.load(update_file, cls=StateDecoder))
