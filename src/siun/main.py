#!/usr/bin/env python

"""siun - check for updates."""

import datetime
import subprocess
from typing import Any

import click

from siun import __version__
from siun.config import Threshold, get_config
from siun.errors import (
    CmdRunError,
    ConfigError,
    CriterionError,
    SiunCLIError,
    SiunGetUpdatesError,
    SiunStateUpdateError,
)
from siun.formatting import Formatter, OutputFormat
from siun.state import Updates

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _get_available_updates(cmd: str) -> list[str] | None:
    try:
        available_updates_run = subprocess.run(  # noqa: S602
            cmd,
            check=True,
            capture_output=True,
            text=True,
            shell=True,
        )
        return available_updates_run.stdout.splitlines()

    except subprocess.CalledProcessError as error:
        raise CmdRunError(error.stderr) from error
    except FileNotFoundError as error:
        raise CmdRunError(error) from error


def _update_state(siun_state: Updates, cmd_available: str) -> None:
    try:
        siun_state.update(available_updates=_get_available_updates(cmd=cmd_available))
    except CmdRunError as error:
        message = f"failed to query available updates: {error}"
        raise SiunStateUpdateError(message) from error
    except CriterionError as error:
        message = f"failed to check criterion [{error.criterion_name}]: {error.message}"
        raise SiunStateUpdateError(message) from error


def _get_updates(
    *,
    no_cache: bool,
    no_update: bool,
    cmd_available: str,
    criteria: dict[str, Any],
    thresholds: dict[Threshold, int],
    cache_min_age_minutes: int,
) -> Updates:
    siun_state = Updates(criteria_settings=criteria, thresholds_settings=thresholds)
    if no_cache:
        if no_update:
            return siun_state

        try:
            _update_state(siun_state, cmd_available)
        except SiunStateUpdateError as error:
            raise SiunGetUpdatesError(error.message) from error
        return siun_state

    now = datetime.datetime.now(tz=datetime.UTC)
    cache_min_age = datetime.timedelta(minutes=cache_min_age_minutes)
    existing_state = Updates.read_state()
    if existing_state:
        siun_state = Updates(thresholds_settings=thresholds, **dict(existing_state))
    if no_update:
        return siun_state

    is_stale = existing_state and existing_state.last_update < (now - cache_min_age)
    if not existing_state or (existing_state and is_stale):
        try:
            _update_state(siun_state, cmd_available)
        except SiunStateUpdateError as error:
            raise SiunGetUpdatesError(error.message) from error
        try:
            siun_state.persist_state()
        except Exception as error:
            message = f"failed to write state to disk: {error}"
            raise SiunGetUpdatesError(message) from error

    return siun_state


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__)
def cli():  # noqa: D103
    pass


@cli.command()
@click.option("--quiet", "-q", is_flag=True, show_default=True, default=False, help="Suppress output")
@click.option("--no-update", "-U", is_flag=True, show_default=True, default=False, help="Don't get updates, only check")
@click.option("--cache/--no-cache", " /-n", show_default=True, default=True, help="Ignore existing state on disk")
@click.option(
    "--output-format", "-o", default="plain", type=click.Choice([of.value for of in OutputFormat], case_sensitive=False)
)
def check(*, output_format: str, cache: bool, no_update: bool, quiet: bool):
    """Check for urgency of available updates."""
    if no_update and not cache:
        raise SiunCLIError(message="--no-update and --no-cache options are mutually exclusive")

    config = None
    try:
        config = get_config()
    except ConfigError as error:
        message = f"{error.message}; config path: {error.config_path}"
        raise SiunCLIError(message) from error

    cmd_available = config.cmd_available
    try:
        siun_state = _get_updates(
            no_cache=not cache,
            no_update=no_update,
            cmd_available=cmd_available,
            criteria=config.criteria,
            thresholds=config.thresholds,
            cache_min_age_minutes=config.cache_min_age_minutes,
        )
    except SiunGetUpdatesError as error:
        raise SiunCLIError(error.message) from error

    formatter = Formatter()
    formatter_kwargs = {}
    if output_format == OutputFormat.CUSTOM.value:
        formatter_kwargs["template_string"] = config.custom_format
    output, output_kwargs = getattr(formatter, f"format_{output_format}")(siun_state.format_object, **formatter_kwargs)
    if not quiet:
        click.secho(output, **output_kwargs)


if __name__ == "__main__":
    cli()
