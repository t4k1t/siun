import datetime
import json
import os
import shutil
import tempfile
from enum import Enum
from importlib.machinery import SourceFileLoader
from pathlib import Path

from siun.criteria import CriterionAvailable, CriterionCount, CriterionCritical, CriterionLastupdate

BUILTIN_CRITERIA = {
    "available": CriterionAvailable(),
    "count": CriterionCount(),
    "critical": CriterionCritical(),
    "lastupdate": CriterionLastupdate(),
}
EXPECTED_CLASS = "SiunCriterion"


def _load_user_criteria(criteria_settings) -> dict:
    """Load user criteria."""
    user_criteria = {}
    enabled_criteria = []
    include_path = Path().home() / ".config" / "siun" / "criteria"

    if not include_path.exists():
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
        class_inst = None
        py_mod = SourceFileLoader(file_path.stem, file_path.as_posix()).load_module()
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


class StateText(Enum):
    """Translate state to text representation."""

    OK = "Ok"
    AVAILABLE_UPDATES = "Updates available"
    WARNING_UPDATES = "Updates recommended"
    CRITICAL_UPDATES = "Updates required"


class StateColor(Enum):
    """Translate state to color."""

    OK = "green"
    AVAILABLE_UPDATES = "blue"
    WARNING_UPDATES = "yellow"
    CRITICAL_UPDATES = "red"


class StateEncoder(json.JSONEncoder):
    """Custom state encoder.

    Serializes Enum and datetime types to JSON.
    """

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

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, *args, **kwargs, object_hook=self._custom_object_hook)

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

    def __init__(self, *, criteria_settings: dict, thresholds_settings: dict):
        self._track_update()
        self.criteria_settings = criteria_settings
        self.thresholds = {
            threshold: State(f"{name.upper()}_UPDATES").name for name, threshold in thresholds_settings.items()
        }
        self.available_updates = []
        self.matched_criteria = {}
        self.state = State.OK

    def _track_update(self):
        self.last_update = datetime.datetime.now(tz=datetime.timezone.utc)

    @property
    def score(self):
        """Calculate score from criteria weights."""
        return sum([criterium["weight"] for criterium in self.matched_criteria.values()])

    @property
    def count(self):
        """Get count of available updates."""
        return len(self.available_updates)

    @property
    def color(self):
        """Get color based on state."""
        return getattr(StateColor, self.state.name)

    @property
    def text_value(self):
        """Get text value based on state."""
        return getattr(StateText, self.state.name)

    def update(self, available_updates: list | None = None):
        """Update state of updates."""
        self._track_update()
        if available_updates is None:
            available_updates = []

        self.available_updates = available_updates

        # Load criteria
        criteria = BUILTIN_CRITERIA
        user_criteria = _load_user_criteria(self.criteria_settings)
        # NOTE: It's possible to overload builtin criteria this way
        criteria.update(user_criteria)

        # Check criteria
        for name, criterion in criteria.items():
            if criterion.is_fulfilled(self.criteria_settings, available_updates):
                self.matched_criteria[name] = {"weight": self.criteria_settings[f"{name}_weight"]}

        thresholds = reversed(self.thresholds.keys())
        for threshold in thresholds:
            if self.score >= threshold:
                self.state = State(self.thresholds[threshold])
                break

    def persist_state(self):
        """Write state to disk.

        Avoids partially written state file (and therefore invalid JSON) by
        creating a temporary file first and only replacing the state file once
        the writing operation is done.
        """
        tempdir = tempfile.gettempdir()
        update_file_path = Path("/".join([tempdir, "siun-state.json"]))
        with tempfile.NamedTemporaryFile(mode="w+") as update_file:
            json.dump(self.__dict__, update_file, cls=StateEncoder)
            update_file.flush()
            shutil.copy(update_file.name, update_file_path)

    @classmethod
    def read_state(cls):
        """Read state from disk."""
        tempdir = tempfile.gettempdir()
        update_file_path = Path("/".join([tempdir, "siun-state.json"]))
        if not update_file_path.exists():
            return None

        with open(update_file_path) as update_file:
            return json.load(update_file, cls=StateDecoder)


def _reverse_readline(filename, buf_size=8192):
    """Return a generator that returns the lines of a file in reverse order.

    https://stackoverflow.com/a/23646049
    """
    with open(filename, "rb") as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            buffer = fh.read(min(remaining_size, buf_size))
            # Remove file's last "\n" if it exists, only for the first buffer
            if remaining_size == file_size and buffer[-1] == ord("\n"):
                buffer = buffer[:-1]
            remaining_size -= buf_size
            lines = buffer.split(b"\n")
            # Append last chunk's segment to this chunk's last line
            if segment is not None:
                lines[-1] += segment
            segment = lines[0]
            lines = lines[1:]
            # Yield lines in this chunk except the segment
            for line in reversed(lines):
                # Only decode on a parsed line, to avoid utf-8 decode error
                yield line.decode()
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment.decode()
