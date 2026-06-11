"""CLI utils."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from siun.config import SiunConfig, get_config
from siun.criteria import SiunCriterion
from siun.errors import (
    ConfigError,
    SiunCLIError,
)
from siun.models.criteria import V2Criterion


def common_options(f: Callable[..., Any]) -> Callable[..., Any]:
    """Define common options for CLI commands."""
    f = click.option(
        "--config-path",
        "-C",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        help="Override config file location.",
    )(f)
    return f


def load_config_or_exit(config_path: Path | None) -> SiunConfig:
    """Load configuration or exit with error."""
    try:
        config = get_config(config_path)
    except ConfigError as error:
        message = f"{error.message}; config path: {error.config_path}"
        raise SiunCLIError(message) from error
    return config


def print_criteria(
    *,
    criteria: dict[str, SiunCriterion],
    criteria_config: list[V2Criterion],
    registry: dict[str, type[V2Criterion]],
) -> None:
    """Print available criteria from config and registry."""
    # TODO: Future: Replace `custom` in available criteria with available custom criteria on disk
    all_names = set(criteria) | set(registry)
    max_name_len = max((len(name) for name in all_names), default=0)
    kind_len = max(len("builtin"), len("custom"))
    override_len = len("OVERRIDES BUILTIN")
    header = (
        f"{'KIND'.ljust(kind_len)}   {'NAME'.ljust(max_name_len)}  {'OVERRIDES BUILTIN'.ljust(override_len)}   CONFIG"
    )
    crit_config_map = {crit.name: crit for crit in criteria_config}
    non_config_fields = {"is_custom"}

    click.echo("Configured criteria:")
    click.echo(f"  {header}")
    click.echo(f"  {'-' * kind_len}   {'-' * max_name_len}  {'-' * override_len}   {'-' * 55}")

    for name, crit in criteria.items():
        is_custom = crit.__class__.__name__ == "SiunCriterion"
        kind = "custom" if is_custom else "builtin"
        overrides = "yes" if is_custom and name in registry else ""
        config = "-"
        if name in crit_config_map:
            extras = {k: v for k, v in crit_config_map[name].model_dump().items() if k not in non_config_fields}
            if extras:
                config = json.dumps(extras, ensure_ascii=False)
        click.echo(f"  {kind.ljust(kind_len)}   {name.ljust(max_name_len)}  {overrides.ljust(override_len)}   {config}")

    click.echo("\nAvailable criteria:")
    for name in sorted(registry):
        click.echo(f"  {name}")
