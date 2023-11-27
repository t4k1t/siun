import datetime
import json
import re
import tempfile
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class StateText(Enum):
    OK = "Ok"
    AVAILABLE_UPDATES = "Updates available"
    WARNING_UPDATES = "Updates recommended"
    CRITICAL_UPDATES = "Updates required"


class StateColor(Enum):
    OK = "green"
    AVAILABLE_UPDATES = "blue"
    WARNING_UPDATES = "yellow"
    CRITICAL_UPDATES = "red"


@dataclass
class UpdateState:
    available_updates: list
    score: int = 0
    count: int = 0
    text_value: StateText = StateText.OK
    color: StateColor = StateColor.OK
    last_update: datetime or None = None


class StateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return {"py-type": type(obj).__name__, "value": obj.value}
        if isinstance(obj, datetime.datetime):
            return {"py-type": type(obj).__name__, "value": obj.isoformat()}

        return json.JSONEncoder.default(self, obj)


class StateDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, *args, **kwargs, object_hook=self.object_hook)

    def object_hook(self, obj):
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
    __slots__ = ("state", "thresholds", "criteria_settings")

    def __init__(self, thresholds: dict, criteria_settings: dict):
        self.thresholds = thresholds
        self.state = UpdateState(available_updates=[])
        self.criteria_settings = criteria_settings

    def update(self, available_updates: Optional[list] = None):
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

        last_threshold = list(self.thresholds.keys())[-1]
        if self.state.score >= last_threshold:
            self.state.text_value = StateText[self.thresholds[last_threshold]]
            self.state.color = StateColor[self.thresholds[last_threshold]]
        else:
            self.state.text_value = StateText[self.thresholds[self.state.score]]
            self.state.color = StateColor[self.thresholds[self.state.score]]
        self.state.last_update = datetime.datetime.now(tz=datetime.timezone.utc)

    def _criteria_count(self):
        return len(self.state.available_updates) > self.criteria_settings["count_threshold"]

    def _criteria_critical(self):
        regex = re.compile(self.criteria_settings["critical_pattern"])
        matches = list(filter(regex.match, self.state.available_updates))

        return bool(matches)

    def persist_state(self):
        tempdir = tempfile.gettempdir()
        update_file_path = Path("/".join([tempdir, "siun-state.json"]))
        with open(update_file_path, "w+") as update_file:
            json.dump(asdict(self.state), update_file, cls=StateEncoder)

    @classmethod
    def read_state(cls):
        tempdir = tempfile.gettempdir()
        update_file_path = Path("/".join([tempdir, "siun-state.json"]))
        if not update_file_path.exists():
            return None

        with open(update_file_path) as update_file:
            return json.load(update_file, cls=StateDecoder)
