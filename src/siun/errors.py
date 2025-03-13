"""Custom error module."""

from pathlib import Path
from typing import final

from click import ClickException


class CmdRunError(Exception):
    """Wrap Exception for calls to 3rd party binaries."""


@final
class CriterionError(Exception):
    """Wrap Exception for criterion errors."""

    def __init__(self, message: str, criterion_name: str | None):
        super().__init__(message)
        self.message = message
        self.criterion_name = criterion_name


@final
class ConfigError(Exception):
    """Custom error type for configuration issues."""

    def __init__(self, message: str, config_path: Path):
        super().__init__(message)
        self.message = message
        self.config_path = config_path


@final
class SiunStateUpdateError(Exception):
    """Wrap Exception for errors on updating the internal state."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@final
class SiunGetUpdatesError(Exception):
    """Wrap Exception for errors on getting available updates."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class SiunCLIError(ClickException):
    """Wrap ClickException for explicit abort on error."""
