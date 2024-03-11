import json
from enum import Enum

from siun.state import Updates


class OutputFormat(Enum):
    """Output format options."""

    PLAIN = "plain"
    FANCY = "fancy"
    JSON = "json"
    I3STATUS = "i3status"


class Formatter:
    """Build output format."""

    @staticmethod
    def format_plain(state: Updates):
        """Build simple text format."""
        return state.text_value.value, {}

    @staticmethod
    def format_fancy(state: Updates):
        """Build coloured text format."""
        return state.text_value.value, {"fg": state.color.value}

    @staticmethod
    def format_json(state: Updates):
        """Build JSON output format."""
        state_dict = {"count": state.count, "text_value": state.text_value.value, "score": state.score}
        return json.dumps(state_dict), {}

    @staticmethod
    def format_i3status(state: Updates):
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
            "WARNING_UPDATES": ",".join([match[:2] for match in state.matched_criteria.keys()]),
            "CRITICAL_UPDATES": ",".join([match[:2] for match in state.matched_criteria.keys()]),
            "UNKNOWN": "…",
        }
        i3status_data = {
            "icon": "archive",
            "state": i3status_state_map[state.text_value.name],
            "text": i3status_text_map[state.text_value.name],
        }
        return json.dumps(i3status_data), {}
