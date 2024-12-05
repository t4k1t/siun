"""Output formatters."""

import json
from enum import Enum
from string import Template
from typing import Never

from siun.state import FormatObject


class OutputFormat(Enum):
    """Output format options."""

    PLAIN = "plain"
    FANCY = "fancy"
    JSON = "json"
    I3STATUS = "i3status"
    CUSTOM = "custom"


class Formatter:
    """Build output format."""

    @staticmethod
    def format_plain(format_object: FormatObject) -> tuple[str, dict[Never, Never]]:
        """Build simple text format."""
        return format_object.status_text, {}

    @staticmethod
    def format_fancy(format_object: FormatObject) -> tuple[str, dict[str, str]]:
        """Build coloured text format."""
        return format_object.status_text, {"fg": format_object.state_color}

    @staticmethod
    def format_json(format_object: FormatObject) -> tuple[str, dict[Never, Never]]:
        """Build JSON output format."""
        state_dict = {
            "count": format_object.update_count,
            "text_value": format_object.status_text,
            "score": format_object.score,
        }
        return json.dumps(state_dict), {}

    @staticmethod
    def format_i3status(format_object: FormatObject) -> tuple[str, dict[Never, Never]]:
        """Build output format for i3status."""
        i3status_state_map = {
            "OK": "Idle",
            "AVAILABLE_UPDATES": "Idle",
            "WARNING_UPDATES": "Warning",
            "CRITICAL_UPDATES": "Critical",
            "UNKNOWN": "Idle",
        }
        i3status_text_map = {
            "OK": "",
            "AVAILABLE_UPDATES": "",
            "WARNING_UPDATES": format_object.matched_criteria_short,
            "CRITICAL_UPDATES": format_object.matched_criteria_short,
            "UNKNOWN": "…",
        }
        i3status_data = {
            "icon": "archive",
            "state": i3status_state_map[format_object.state_name],
            "text": i3status_text_map[format_object.state_name],
        }
        return json.dumps(i3status_data), {}

    @staticmethod
    def format_custom(format_object: FormatObject, template_string: str) -> tuple[str, dict[Never, Never]]:
        """Build customised output format."""
        format_template = Template(template_string)
        output = format_template.safe_substitute(**format_object.model_dump())
        return output, {}
