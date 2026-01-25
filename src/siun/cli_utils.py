"""CLI utils."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from siun.config import SiunConfig, get_config
from siun.errors import (
    ConfigError,
    SiunCLIError,
)


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
