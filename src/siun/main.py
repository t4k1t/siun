#!/usr/bin/env python

"""siun - Know how urgently your system needs to be updated."""

import datetime
import subprocess
from pathlib import Path
from typing import Any

import click

from siun import __version__
from siun.config import SiunConfig, get_config
from siun.errors import (
    CmdRunError,
    ConfigError,
    CriterionError,
    SiunCLIError,
    SiunGetUpdatesError,
    SiunNotificationError,
    SiunStateUpdateError,
)
from siun.formatting import Formatter, OutputFormat
from siun.models import V2Threshold
from siun.notification import INSTALLED_FEATURES as INSTALLED_NOTIFICATION_FEATURES
from siun.state import FormatObject, Updates, load_state

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
INSTALLED_FEATURES: set[str] = INSTALLED_NOTIFICATION_FEATURES


def get_formatted_state_text(format_object: FormatObject, output_format: str, custom_format: str) -> str:
    """Generate formatted output text from update state."""
    formatter = Formatter()
    formatter_kwargs = {}
    if output_format == OutputFormat.CUSTOM.value:
        formatter_kwargs["template_string"] = custom_format
    formatted_output, format_options = getattr(formatter, f"format_{output_format}")(format_object, **formatter_kwargs)
    return click.style(formatted_output, **format_options)


def fetch_available_updates(cmd: str) -> list[str] | None:
    """Run external command to get list of available updates."""
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


def update_state_with_available_packages(siun_state: Updates, cmd_available: str) -> None:
    """Fetch available package updates an (re-)evaluate update state."""
    try:
        siun_state.evaluate(available_updates=fetch_available_updates(cmd_available))
    except CmdRunError as error:
        message = f"failed to query available updates: {error}"
        raise SiunStateUpdateError(message) from error
    except CriterionError as error:
        message = f"failed to check criterion [{error.criterion_name}]: {error.message}"
        raise SiunStateUpdateError(message) from error


# TODO: Update CHANGELOG, examples
# TODO: Refactor: split
def _get_updates(
    *,
    no_cache: bool,
    no_update: bool,
    cmd_available: str,
    criteria: dict[str, Any],
    thresholds: list[V2Threshold],
    cache_min_age_minutes: int,
    state_file_path: Path,
) -> Updates:
    siun_state = Updates(criteria_settings=criteria, thresholds=thresholds)
    if no_cache:
        if no_update:
            # NOTE: The CLI forbids the combination of no_cache and no_update, but there is not reason to fail here
            return siun_state

        try:
            update_state_with_available_packages(siun_state, cmd_available)
        except SiunStateUpdateError as error:
            raise SiunGetUpdatesError(error.message) from error
        return siun_state

    now = datetime.datetime.now(tz=datetime.UTC)
    cache_min_age = datetime.timedelta(minutes=cache_min_age_minutes)
    existing_state = load_state(state_file_path)
    is_stale = existing_state and existing_state.last_update < (now - cache_min_age)

    if existing_state:
        siun_state = existing_state
        siun_state.last_match = siun_state.match
        siun_state.thresholds = thresholds  # Update thresholds from config
        siun_state.criteria_settings = criteria  # Update criteria from config
        try:
            siun_state.evaluate(available_updates=existing_state.available_updates)
        except SiunStateUpdateError as error:
            raise SiunGetUpdatesError(error.message) from error

    if no_update:
        return siun_state

    if not existing_state or (existing_state and is_stale):
        try:
            update_state_with_available_packages(siun_state, cmd_available)
        except SiunStateUpdateError as error:
            raise SiunGetUpdatesError(error.message) from error
        try:
            siun_state.persist_state(state_file_path)
        except Exception as error:
            message = f"failed to write state to disk: {error}"
            raise SiunGetUpdatesError(message) from error

    return siun_state


def _handle_notification(config: SiunConfig, siun_state: Updates) -> None:
    notification = config.notification
    if not notification:
        return None

    if "notification" not in INSTALLED_FEATURES:
        message = "notifications require the 'notification' feature, install with 'pip install siun[notification]'"
        raise SiunNotificationError(message)

    threshold_score = config.mapped_thresholds[notification.threshold].score
    if (
        not siun_state.match
        or (siun_state.last_match and siun_state.match.score <= siun_state.last_match.score)
        or siun_state.match.score <= threshold_score
    ):
        return None

    notification.fill_templates(siun_state.format_object)
    if notification.urgency is not None:
        notification.hints = {"urgency": notification.urgency.value}
    notification.show()


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__)
def cli():  # noqa: D103 # pragma: no cover
    pass


@cli.command()
@click.option(
    "--config-path",
    "-C",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="Override config file location",
)
@click.option("--quiet", "-q", is_flag=True, show_default=True, default=False, help="Suppress output")
@click.option("--no-update", "-U", is_flag=True, show_default=True, default=False, help="Don't get updates, only check")
@click.option("--cache/--no-cache", " /-n", show_default=True, default=True, help="Ignore existing state on disk")
@click.option(
    "--output-format", "-o", default="plain", type=click.Choice([of.value for of in OutputFormat], case_sensitive=False)
)
def check(*, output_format: str, cache: bool, no_update: bool, quiet: bool, config_path: Path):
    """Check for urgency of available updates."""
    if no_update and not cache:
        raise SiunCLIError(message="--no-update and --no-cache options are mutually exclusive")

    config = None
    try:
        config = get_config(config_path)
    except ConfigError as error:
        message = f"{error.message}; config path: {error.config_path}"
        raise SiunCLIError(message) from error

    try:
        siun_state = _get_updates(
            no_cache=not cache,
            no_update=no_update,
            cmd_available=config.cmd_available,
            criteria=config.criteria,
            thresholds=config.sorted_thresholds,
            cache_min_age_minutes=config.cache_min_age_minutes,
            state_file_path=config.state_file,
        )
    except SiunGetUpdatesError as error:
        raise SiunCLIError(error.message) from error

    if not quiet:
        formatted_output = get_formatted_state_text(siun_state.format_object, output_format, config.custom_format)
        click.echo(formatted_output)

    try:
        _handle_notification(config, siun_state)
    except SiunNotificationError as error:
        raise SiunCLIError(error.message) from error


if __name__ == "__main__":  # pragma: no cover
    cli()
