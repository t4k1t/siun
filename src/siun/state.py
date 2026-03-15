"""Internal state of siun and available updates."""

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any

from siun.criteria import CriterionAvailable, CriterionCount, CriterionPattern, SiunCriterion
from siun.errors import CriterionError
from siun.models import PackageUpdate, V2Criterion
from siun.models.updates import Updates
from siun.providers import UpdateProvider
from siun.util import get_default_criteria_dir, is_path_world_writable

BUILTIN_CRITERIA: dict[str, SiunCriterion] = {
    "available": CriterionAvailable(),
    "count": CriterionCount(),
    "pattern": CriterionPattern(),
}
EXPECTED_CLASS = "SiunCriterion"

Updates.model_rebuild()


def _load_user_criteria(*, criteria_settings: list[V2Criterion], include_path: Path | None = None) -> dict[str, Any]:
    """Load user criteria."""
    user_criteria: dict[str, SiunCriterion] = {}
    if not include_path:
        include_path = get_default_criteria_dir()

    if not include_path.exists() or not include_path.is_dir():
        return user_criteria

    if is_path_world_writable(include_path):
        message = (
            f"Criteria directory '{include_path}' is world-writable. "
            "Please change its permissions to be more restrictive."
        )
        raise ImportError(message)

    # Get list of enabled user criteria from config
    enabled_criteria = {criterion.name for criterion in criteria_settings if criterion.weight != 0}

    for f_name in include_path.iterdir():
        # Only load enabled user criteria
        if f_name.suffix != ".py" or f_name.stem not in enabled_criteria:
            continue  # Skip non-Python files
        file_path = include_path / f_name
        py_mod_loader = SourceFileLoader(file_path.stem, file_path.as_posix())
        py_mod_spec = importlib.util.spec_from_loader(py_mod_loader.name, py_mod_loader)
        if py_mod_spec is None:
            message = "Could not create module specification for source file loader"
            raise ImportError(message)
        py_mod = importlib.util.module_from_spec(py_mod_spec)
        py_mod_loader.exec_module(py_mod)
        if hasattr(py_mod, EXPECTED_CLASS):
            # Check inheritance
            class_obj = getattr(py_mod, EXPECTED_CLASS)
            if not hasattr(class_obj, "is_fulfilled") or not callable(class_obj.is_fulfilled):
                continue  # An error is raised later if any configured criteria could not be loaded
            class_inst = py_mod.SiunCriterion()
            user_criteria[file_path.stem] = class_inst

    return user_criteria


def load_state(state_file_path: Path) -> Updates | None:
    """Read state from disk."""
    if not state_file_path.exists():
        return None

    with Path.open(state_file_path) as update_file:
        return Updates.model_validate_json(update_file.read())


def get_package_updates(update_providers: list[UpdateProvider]) -> list[PackageUpdate]:
    """Fetch available package updates."""
    package_updates: list[PackageUpdate] = []
    for provider in update_providers:
        package_updates.extend(provider.fetch_updates())

    return package_updates


def get_merged_criteria(criteria_settings: list[V2Criterion]) -> dict[str, SiunCriterion]:
    """Return merged built-in and user criteria."""
    try:
        criteria = BUILTIN_CRITERIA.copy()
        user_criteria = _load_user_criteria(criteria_settings=criteria_settings)
        criteria.update(user_criteria)
    except Exception as error:
        message = f"Error loading criteria: {error}"
        raise CriterionError(message, None) from error

    return criteria
