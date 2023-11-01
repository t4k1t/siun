#!/usr/bin/env python

"""siun - check for pacman updates."""

import collections.abc
import datetime
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import click
import tomllib

CMD_AVAILABLE = "pacman -Quq"


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


class OutputFormat(Enum):
    PLAIN = "plain"
    FANCY = "fancy"
    JSON = "json"
    I3STATUS = "i3status"


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
            self.state.score += 1
        if self._criteria_critical():
            self.state.score += 1

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


def _get_available_updates():
    cmd = ["pacman", "-Quq"]
    if CMD_AVAILABLE:
        cmd = CMD_AVAILABLE.split(" ")
    try:
        available_updates_run = subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa
        return available_updates_run.stdout.splitlines()

    except subprocess.CalledProcessError as error:
        if error.returncode == 1 and not error.stdout and not error.stderr:
            # pacman exits with code 1 if there are no updates
            return []

        click.echo(f"Failed to query available updates: {error.stderr}", err=True, nl=False)
        sys.exit(1)


def _persist_state(updates: Updates):
    tempdir = tempfile.gettempdir()
    update_file_path = Path("/".join([tempdir, "siun-state.json"]))
    with open(update_file_path, "w+") as update_file:
        json.dump(asdict(updates.state), update_file, cls=StateEncoder)


def _read_state():
    tempdir = tempfile.gettempdir()
    update_file_path = Path("/".join([tempdir, "siun-state.json"]))
    if not update_file_path.exists():
        return None

    with open(update_file_path) as update_file:
        return json.load(update_file, cls=StateDecoder)


class Formatter:
    @staticmethod
    def format_plain(state: UpdateState):
        return state.text_value.value, {}

    @staticmethod
    def format_fancy(state: UpdateState):
        return state.text_value.value, {"fg": state.color.value}

    @staticmethod
    def format_json(state: UpdateState):
        state_dict = {"count": state.count, "text_value": state.text_value.value, "score": state.score}
        return json.dumps(state_dict), {}

    @staticmethod
    def format_i3status(state: UpdateState):
        i3status_state_map = {
            "OK": "Idle",
            "AVAILABLE_UPDATES": "Idle",
            "WARNING_UPDATES": "Warning",
            "CRITICAL_UPDATES": "Critical",
        }
        i3status_text_map = {
            "OK": "",
            "AVAILABLE_UPDATES": "",
            "WARNING_UPDATES": "Updates recommended",
            "CRITICAL_UPDATES": "Updates required",
        }
        i3status_data = {
            "icon": "archive",
            "state": i3status_state_map[state.text_value.name],
            "text": i3status_text_map[state.text_value.name],
        }
        return json.dumps(i3status_data), {}


def load_config():
    # TODO: error handling
    with open(Path().home() / ".config" / "siun.toml", "rb") as file_obj:
        return tomllib.load(file_obj)


def update_nested(d, u):
    # Preserve existing keys of nested dicts
    # https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update_nested(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def main(*, output_format: str):
    """Main function."""
    config = {
        "cmd_available": "pacman -Quq",
        "criteria": {
            "critical_pattern": "^archlinux-keyring$|^linux$|^firefox$|^pacman.*$",
            "critical_weight": 1,
            "count_threshold": 15,
            "count_weight": 1,
            "lastupdate_age_seconds": 604800,  # 7 days
            "lastupdate_weight": 1,
        }
    }
    user_config = load_config()
    config = update_nested(config, user_config)

    thresholds = {0: "OK", 1: "AVAILABLE_UPDATES", 2: "WARNING_UPDATES", 3: "CRITICAL_UPDATES"}

    updates = Updates(thresholds=thresholds, criteria_settings=config["criteria"])
    existing_state = _read_state()
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if existing_state and (existing_state["last_update"] > (now - datetime.timedelta(minutes=30))):
        updates.update(available_updates=existing_state["available_updates"])
    else:
        updates.update(available_updates=_get_available_updates())
        _persist_state(updates)

    output = ""
    output_kwargs = {}
    formatter = Formatter()
    output, output_kwargs = getattr(formatter, f"format_{output_format}")(updates.state)
    click.secho(output, **output_kwargs)


@click.command()
@click.option(
    "--output-format", default="plain", type=click.Choice([of.value for of in OutputFormat], case_sensitive=False)
)
def cli(output_format):
    main(output_format=output_format)


if __name__ == "__main__":
    cli()
