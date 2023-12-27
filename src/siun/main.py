#!/usr/bin/env python

"""siun - check for pacman updates."""

import collections.abc
import datetime
import subprocess
import sys
from pathlib import Path

import click
import tomllib

from siun.formatting import Formatter, OutputFormat
from siun.state import StateText, Updates

CMD_AVAILABLE = "pacman -Quq"


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

        panic(f"Failed to query available updates: {error.stderr}")


def panic(message):
    """Write message to stderr and exit."""
    click.echo(message, err=True, nl=False)
    sys.exit(1)


def load_config():
    """Read config from disk."""
    with open(Path().home() / ".config" / "siun.toml", "rb") as file_obj:
        return tomllib.load(file_obj)


def update_nested(d, u):
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
    default_config = {
        "cmd_available": "pacman -Quq",
        "criteria": {
            "critical_pattern": "^archlinux-keyring$|^linux$|^firefox$|^pacman.*$",
            "critical_weight": 1,
            "count_threshold": 15,
            "count_weight": 1,
            "lastupdate_age_hours": 618,  # 7 days
            "lastupdate_weight": 1,
        },
    }
    try:
        user_config = load_config()
        config = update_nested(default_config, user_config)
    except OSError as error:
        panic(f"Failed to open config file for reading: {error}")
    except tomllib.TOMLDecodeError as error:
        panic(f"Provided config file not valid: {error}")

    thresholds = {
        0: StateText.OK.name,
        1: StateText.AVAILABLE_UPDATES.name,
        2: StateText.WARNING_UPDATES.name,
        3: StateText.CRITICAL_UPDATES.name,
    }

    updates = Updates(thresholds=thresholds, criteria_settings=config["criteria"])
    existing_state = Updates.read_state()
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if existing_state and (existing_state["last_update"] > (now - datetime.timedelta(minutes=30))):
        updates.update(available_updates=existing_state["available_updates"])
    else:
        updates.update(available_updates=_get_available_updates())
        updates.persist_state()

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
    """Run main with CLI args."""
    main(output_format=output_format)


if __name__ == "__main__":
    cli()
