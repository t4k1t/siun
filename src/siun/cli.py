"""CLI commands for siun."""

import datetime
import json
from collections import defaultdict
from pathlib import Path

import click

from siun import __version__
from siun.cli_utils import common_options, load_config_or_exit
from siun.config import SiunConfig
from siun.errors import (
    SiunCLIError,
    SiunGetUpdatesError,
    SiunNotificationError,
    SiunStateUpdateError,
)
from siun.formatting import Formatter, OutputFormat
from siun.models import ClickColor, FormatObject, NewsEntry, NewsProvider, V2Criterion, V2Threshold
from siun.news import INSTALLED_FEATURES as INSTALLED_NEWS_FEATURES
from siun.news import parse_feed_entries
from siun.notification import INSTALLED_FEATURES as INSTALLED_NOTIFICATION_FEATURES
from siun.providers import UpdateProvider
from siun.state import Updates, load_state, update_state_with_available_packages
from siun.util import safely_write_to_disk

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
INSTALLED_FEATURES: set[str] = INSTALLED_NOTIFICATION_FEATURES | INSTALLED_NEWS_FEATURES


def get_formatted_state_text(format_object: FormatObject, output_format: OutputFormat, custom_format: str) -> str:
    """Generate formatted output text from update state."""
    formatter = Formatter()
    formatter_kwargs = {}
    if output_format == OutputFormat.CUSTOM:
        formatter_kwargs["template_string"] = custom_format
    formatted_output, format_options = getattr(formatter, f"format_{output_format.value}")(
        format_object, **formatter_kwargs
    )
    return click.style(formatted_output, **format_options)


def _get_updates(
    *,
    no_cache: bool,
    no_update: bool,
    criteria: list[V2Criterion],
    thresholds: list[V2Threshold],
    cache_min_age_minutes: int,
    state_file_path: Path,
    update_providers: list[UpdateProvider],
) -> Updates:
    siun_state = Updates(criteria_settings=criteria, thresholds=thresholds)

    if no_cache:
        if no_update:
            return siun_state
        try:
            update_state_with_available_packages(siun_state, update_providers)
        except SiunStateUpdateError as error:
            raise SiunGetUpdatesError(error.message) from error
        return siun_state

    now = datetime.datetime.now(tz=datetime.UTC)
    cache_min_age = datetime.timedelta(minutes=cache_min_age_minutes)
    existing_state = load_state(state_file_path)
    is_stale = existing_state and existing_state.last_update < (now - cache_min_age)
    needs_update = False

    if existing_state:
        siun_state = existing_state
        siun_state.last_match = siun_state.match
        siun_state.thresholds = thresholds
        siun_state.criteria_settings = criteria
        try:
            siun_state.evaluate(available_updates=existing_state.available_updates)
        except SiunStateUpdateError as error:
            raise SiunGetUpdatesError(error.message) from error
        if siun_state.last_match != siun_state.match:
            needs_update = True

    if no_update:
        return siun_state

    if not existing_state or is_stale:
        try:
            update_state_with_available_packages(siun_state, update_providers)
        except SiunStateUpdateError as error:
            raise SiunGetUpdatesError(error.message) from error
        try:
            siun_state.persist_state(state_file_path)
        except Exception as error:
            message = f"failed to write state to disk: {error}"
            raise SiunGetUpdatesError(message) from error
    elif needs_update:
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
        or siun_state.match.score < threshold_score
    ):
        return None

    notification.fill_templates(siun_state.format_object)
    if notification.urgency is not None:
        notification.hints = {"urgency": notification.urgency.value}
    notification.show()


def _get_last_news_update(*, sources: list[NewsProvider], last_update_path: Path) -> None:
    from_disk: list[dict[str, str]] = []
    if last_update_path.exists() and last_update_path.is_file():
        with last_update_path.open("r", encoding="utf-8") as file_obj:
            try:
                from_disk = json.loads(file_obj.read())
            except json.JSONDecodeError as error:
                raise SiunCLIError(
                    message=f"Failed to parse last news update state from disk; state path: {last_update_path}"
                ) from error
    for source in sources:
        for saved_source in from_disk:
            if source.url == saved_source.get("url", ""):
                source._etag = saved_source.get("etag", None)
                source._last_modified = saved_source.get("last_modified", None)
                if not source.title:
                    source.title = saved_source.get("title", "No title")
                break
    return None


def _write_last_news_update(*, sources: list[NewsProvider], last_update_path: Path) -> None:
    """Write news state to disk."""
    return safely_write_to_disk(
        content=json.dumps(
            [source.model_dump(include={"url", "etag", "last_modified", "title"}) for source in sources]
        ),
        target_path=last_update_path,
    )


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__)
def cli() -> None:  # noqa: D103 # pragma: no cover
    pass


@cli.command()
@click.option("--nocolor", is_flag=True, show_default=True, default=False, help="Do not colorize output.")
@common_options
def news(*, config_path: Path, nocolor: bool) -> None:
    """Show latest news headlines."""
    if "news" not in INSTALLED_FEATURES:
        message = "news require the 'news' feature, install with 'pip install siun[news]'"
        raise SiunCLIError(message)

    config = load_config_or_exit(config_path)
    news_sources = config.news

    last_update_path = config.state_dir / Path("last_news_update")
    # Load ETag and Last-Modified headers from disk
    _get_last_news_update(sources=news_sources, last_update_path=last_update_path)

    news_entries: dict[str, list[NewsEntry]] = defaultdict(list)
    for source in news_sources:
        feed_title, entries = parse_feed_entries(source)
        news_entries[feed_title].extend(entries)

    # Write updated ETag and Last-Modified headers to disk to avoid requesting data we've already seen
    _write_last_news_update(sources=news_sources, last_update_path=last_update_path)

    # Print news entries
    for feed_title, entries in news_entries.items():
        click.echo(click.style(f"{feed_title}:\n", fg=ClickColor.yellow.value if not nocolor else None))
        for entry in entries:
            click.echo(f"- {entry.title}")
            click.echo(click.style(f"  {entry.link}", fg=ClickColor.blue.value if not nocolor else None))
            click.echo(f"  {entry.published_at}\n")
        if not entries:
            click.echo("No new entries.\n")


@cli.command()
@click.option("--quiet", "-q", is_flag=True, show_default=True, default=False, help="Suppress output.")
@click.option(
    "--no-update", "-U", is_flag=True, show_default=True, default=False, help="Don't get updates, only check."
)
@click.option("--cache/--no-cache", " /-n", show_default=True, default=True, help="Ignore existing state on disk.")
@click.option(
    "--output-format",
    "-o",
    default=OutputFormat.PLAIN,
    type=click.Choice(OutputFormat, case_sensitive=False),
    help="Pick output format for update check.",
)
@common_options
def check(*, config_path: Path, output_format: OutputFormat, cache: bool, no_update: bool, quiet: bool) -> None:
    """Check for urgency of available updates."""
    if no_update and not cache:
        raise SiunCLIError(message="--no-update and --no-cache options are mutually exclusive")

    config = load_config_or_exit(config_path)
    try:
        siun_state = _get_updates(
            no_cache=not cache,
            no_update=no_update,
            criteria=config.v2_criteria,
            thresholds=config.sorted_thresholds,
            cache_min_age_minutes=config.cache_min_age_minutes,
            state_file_path=config.state_dir / Path("state.json"),
            update_providers=config.update_providers,
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
