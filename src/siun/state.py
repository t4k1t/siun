import datetime
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


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


@dataclass
class UpdateState:
    """Store state of updates."""

    available_updates: list
    score: int = 0
    count: int = 0
    text_value: StateText = StateText.OK
    color: StateColor = StateColor.OK
    last_update: datetime or None = None


class StateEncoder(json.JSONEncoder):
    """Custom state encoder.

    Serializes Enum and datetime types to JSON.
    """

    def default(self, obj):  # noqa
        if isinstance(obj, Enum):
            return {"py-type": type(obj).__name__, "value": obj.value}
        if isinstance(obj, datetime.datetime):
            return {"py-type": type(obj).__name__, "value": obj.isoformat()}

        return json.JSONEncoder.default(self, obj)


class StateDecoder(json.JSONDecoder):
    """Custom state decoder.

    Deserialize custom python types from JSON.
    """

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, *args, **kwargs, object_hook=self.object_hook)

    def object_hook(self, obj):  # noqa
        pytype = obj.get("py-type")
        if not pytype:
            return obj

        if pytype == "datetime":
            return datetime.datetime.fromisoformat(obj["value"])
        elif pytype in [StateText.__name__, StateColor.__name__]:
            t = globals()[pytype]
            return t(obj["value"])
        else:
            raise NotImplementedError

        return obj


class Updates:
    """Handle available updates."""

    __slots__ = ("state", "thresholds", "criteria_settings")

    def __init__(self, thresholds: dict, criteria_settings: dict):
        self.thresholds = thresholds
        self.state = UpdateState(available_updates=[])
        self.criteria_settings = criteria_settings

    def update(self, available_updates: Optional[list] = None):
        """Update state of updates."""
        self.state.score = 0
        if available_updates is None:
            available_updates = []
        self.state.available_updates = available_updates
        self.state.count = len(available_updates)

        # Are there any updates?
        if self.state.count > 0:
            self.state.score += 1
        # Rest of criteria
        if self._criteria_count():
            self.state.score += self.criteria_settings["count_weight"]
        if self._criteria_critical():
            self.state.score += self.criteria_settings["critical_weight"]
        if self._criteria_last_update():
            self.state.score += self.criteria_settings["lastupdate_weight"]

        last_threshold = list(self.thresholds.keys())[-1]
        if self.state.score >= last_threshold:
            self.state.text_value = StateText[self.thresholds[last_threshold]]
            self.state.color = StateColor[self.thresholds[last_threshold]]
        else:
            self.state.text_value = StateText[self.thresholds[self.state.score]]
            self.state.color = StateColor[self.thresholds[self.state.score]]
        self.state.last_update = datetime.datetime.now(tz=datetime.timezone.utc)

    def _criteria_count(self):
        """Check if count of available updates has exceeded threshold."""
        return len(self.state.available_updates) > self.criteria_settings["count_threshold"]

    def _criteria_critical(self):
        """Check if list of available updates contains critical updates according to pattern."""
        regex = re.compile(self.criteria_settings["critical_pattern"])
        matches = list(filter(regex.match, self.state.available_updates))

        return bool(matches)

    def _criteria_last_update(self):
        """Check if time of last update has exceeded set time period."""
        regex = re.compile(r"^\[([0-9TZ:\+\-]+)\] \[ALPM\] upgraded.*")
        last_update = None
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
            json.dump(asdict(self.state), update_file, cls=StateEncoder)

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
