import datetime
import json
import os
import re
import tempfile
from enum import Enum
from pathlib import Path


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
        # Check criteria
        if self.criteria_settings["available_weight"] > 0 and self._criterion_available(available_updates):
            self.matched_criteria["available"] = {"weight": self.criteria_settings["available_weight"]}
        if self.criteria_settings["count_weight"] > 0 and self._criterion_count(available_updates):
            self.matched_criteria["count"] = {"weight": self.criteria_settings["count_weight"]}
        if self.criteria_settings["critical_weight"] > 0 and self._criterion_critical(available_updates):
            self.matched_criteria["critical"] = {"weight": self.criteria_settings["critical_weight"]}
        if self.criteria_settings["lastupdate_weight"] > 0 and self._criterion_lastupdate(available_updates):
            self.matched_criteria["lastupdate"] = {"weight": self.criteria_settings["lastupdate_weight"]}

        thresholds = reversed(self.thresholds.keys())
        for threshold in thresholds:
            if self.score >= threshold:
                self.state = State(self.thresholds[threshold])
                break

    def _criterion_available(self, available_updates: list):
        """Check if there are any available updates."""
        return bool(available_updates)

    def _criterion_count(self, available_updates: list):
        """Check if count of available updates has exceeded threshold."""
        return len(available_updates) >= self.criteria_settings["count_threshold"]

    def _criterion_critical(self, available_updates: list):
        """Check if list of available updates contains critical updates according to pattern."""
        regex = re.compile(self.criteria_settings["critical_pattern"])
        matches = list(filter(regex.match, available_updates))

        return bool(matches)

    def _criterion_lastupdate(self, available_updates: list):  # noqa: ARG002
        """Check if time of last update has exceeded set time period."""
        regex = re.compile(r"^\[([0-9TZ:\+\-]+)\] \[ALPM\] upgraded.*")
        last_update = False
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        for line in _reverse_readline(Path("/var/log/pacman.log")):
            match = regex.match(line)
            if match:
                last_update = datetime.datetime.fromisoformat(match.group(1))
                break
        return (
            last_update
            and (last_update + datetime.timedelta(hours=self.criteria_settings["lastupdate_age_hours"])) < now
        )

    def persist_state(self):
        """Write state to disk."""
        tempdir = tempfile.gettempdir()
        update_file_path = Path("/".join([tempdir, "siun-state.json"]))
        with open(update_file_path, "w+") as update_file:
            json.dump(self.__dict__, update_file, cls=StateEncoder)

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
