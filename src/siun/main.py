#!/usr/bin/env python

"""siun - check for pacman updates."""

import collections.abc
import datetime
import subprocess
import sys
from pathlib import Path
from typing import Mapping

import click
import tomllib

from siun.formatting import Formatter, OutputFormat
from siun.state import State, Updates


def _get_available_updates(cmd):
    try:
        available_updates_run = subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa
        return available_updates_run.stdout.splitlines()

    except subprocess.CalledProcessError as error:
        if error.returncode == 1 and not error.stdout and not error.stderr:
            # pacman exits with code 1 if there are no updates
            return []

        panic(f"Failed to query available updates: {error.stderr}")


def panic(message: str):
    """Write message to stderr and exit."""
    click.echo(message, err=True, nl=False)
    sys.exit(1)


def load_config():
    """Read config from disk."""
    with open(Path().home() / ".config" / "siun.toml", "rb") as file_obj:
        return tomllib.load(file_obj)


def update_nested(d: dict, u: dict | Mapping):
    """Preserve existing keys of nested dicts.

    https://stackoverflow.com/a/3233356
    """
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update_nested(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def main(*, output_format: str):
    """Check for pacman updates."""
    config = {
        "cmd_available": "pacman -Quq",
        "thresholds ": {"available": 1, "warning": 2, "critical": 3},
        "criteria": {
            "available_weight": 1,
            "critical_pattern": "^archlinux-keyring$|^linux$|^firefox$|^pacman.*$",
            "critical_weight": 1,
            "count_threshold": 15,
            "count_weight": 1,
            "lastupdate_age_hours": 618,  # 7 days
            "lastupdate_weight": 1,
        },
    }
    try:
        # TODO: Validate config values
        user_config = load_config()
        config = update_nested(config, user_config)
    except OSError as error:
        panic(f"Failed to open config file for reading: {error}")
    except tomllib.TOMLDecodeError as error:
        panic(f"Provided config file not valid: {error}")

    cmd_available = config["cmd_available"].split(" ")

    threshold_map = {
        threshold: State(f"{name.upper()}_UPDATES").name for name, threshold in config["thresholds"].items()
    }

    updates = Updates(criteria_settings=config["criteria"], thresholds=threshold_map)
    existing_state = Updates.read_state()
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if existing_state and (existing_state["last_update"] > (now - datetime.timedelta(minutes=30))):
        updates.update(available_updates=existing_state["available_updates"])
    else:
        updates.update(available_updates=_get_available_updates(cmd=cmd_available))
        updates.persist_state()

    output = ""
    output_kwargs = {}
    formatter = Formatter()
    output, output_kwargs = getattr(formatter, f"format_{output_format}")(updates)
    click.secho(output, **output_kwargs)


@click.command()
@click.option(
    "--output-format", default="plain", type=click.Choice([of.value for of in OutputFormat], case_sensitive=False)
)
def cli(output_format: str):
    """Run main with CLI args."""
    main(output_format=output_format)


if __name__ == "__main__":
    cli()
