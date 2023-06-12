#!/usr/bin/env python

"""pacup - check for pacman updates."""

import datetime
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import click


class StateText(Enum):
    OK = "Ok"
    AVAILABLE_UPDATES = "Updates available"
    CRITICAL_UPDATES = "Updates required"


class StateColor(Enum):
    OK = "green"
    AVAILABLE_UPDATES = "yellow"
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
    __slots__ = ("state", "thresholds", "count_threshold", "critical_pattern")

    def __init__(self, thresholds: dict):
        self.count_threshold = 10
        self.critical_pattern = r"^linux.*|^firefox.*"
        self.thresholds = thresholds
        self.state = UpdateState(available_updates=[])

    def update(self, available_updates: list = None):
        self.state.score = 0
        if available_updates is None:
            available_updates = []
        self.state.available_updates = available_updates
        self.state.count = len(available_updates)

        if self._criteria_count():
            click.echo("count criterion matched")
            self.state.score += 1
        if self._criteria_critical():
            click.echo("critical update criterion matched")
            self.state.score += 1

        self.state.text_value = StateText[self.thresholds[self.state.score]]
        self.state.color = StateColor[self.thresholds[self.state.score]]
        self.state.last_update = datetime.datetime.now(tz=datetime.timezone.utc)

    def _criteria_count(self):
        return len(self.state.available_updates) > self.count_threshold

    def _criteria_critical(self):
        regex = re.compile(self.critical_pattern)
        matches = list(filter(regex.match, self.state.available_updates))

        return bool(matches)

    def _criteria_last_update(self):
        # XXX: Not available through CLI, either cache or try to figure out
        # through file system
        raise NotImplementedError

    def _criteria_download_size(self):
        # XXX: Only available via `-Syu` it seems
        raise NotImplementedError


def _sync_packages():
    try:
        subprocess.run(["pacman", "-Sy"], check=True, capture_output=True, text=True)  # noqa
    except subprocess.CalledProcessError as error:
        click.echo(f"Failed to sync packages: {error.stderr}", err=True, nl=False)
        sys.exit(1)


def _get_available_updates():
    try:
        available_updates_run = subprocess.run(["pacman", "-Qu"], check=True, capture_output=True, text=True)  # noqa
        return available_updates_run.stdout.splitlines()
    except subprocess.CalledProcessError as error:
        click.echo(f"Failed to query available updates: {error.stderr}", err=True, nl=False)
        sys.exit(1)


def _persist_state(updates: Updates):
    tempdir = tempfile.gettempdir()
    update_file_path = Path("/".join([tempdir, "pacup-state.json"]))
    with open(update_file_path, "w+") as update_file:
        json.dump(asdict(updates.state), update_file, cls=StateEncoder)


def _read_state():
    tempdir = tempfile.gettempdir()
    update_file_path = Path("/".join([tempdir, "pacup-state.json"]))
    if not update_file_path.exists():
        return None

    with open(update_file_path) as update_file:
        return json.load(update_file, cls=StateDecoder)


def main():
    """Main function."""
    thresholds = {0: "OK", 1: "AVAILABLE_UPDATES", 2: "CRITICAL_UPDATES"}
    updates = Updates(thresholds=thresholds)
    existing_state = _read_state()
    if existing_state:
        click.echo("found existing state")
        updates.update(available_updates=existing_state["available_updates"])
    else:
        click.echo("writing new state")
        updates.update(available_updates=_get_available_updates())
        _persist_state(updates)

    # TODO: default output should just be ok|warning|critical
    # TODO: add flag to also add count to output
    # TODO: add flag to also add matched criteria
    click.secho(
        f"{updates.state.text_value.value}: {updates.state.count}",
        fg=updates.state.color.value,
    )


if __name__ == "__main__":
    main()
