import json
from enum import Enum

from siun.state import UpdateState


class OutputFormat(Enum):
    PLAIN = "plain"
    FANCY = "fancy"
    JSON = "json"
    I3STATUS = "i3status"


class Formatter:
    @staticmethod
    def format_plain(state: UpdateState):
        return state.text_value.value, {}

    @staticmethod
    def format_fancy(state: UpdateState):
        return state.text_value.value, {"fg": state.color.value}

    @staticmethod
    def format_json(state: UpdateState):
        state_dict = {"count": state.count, "text_value": state.text_value.value, "score": state.score}
        return json.dumps(state_dict), {}

    @staticmethod
    def format_i3status(state: UpdateState):
        i3status_state_map = {
            "OK": "Idle",
            "AVAILABLE_UPDATES": "Idle",
            "WARNING_UPDATES": "Warning",
            "CRITICAL_UPDATES": "Critical",
        }
        i3status_text_map = {
            "OK": "",
            "AVAILABLE_UPDATES": "",
            "WARNING_UPDATES": "Updates recommended",
            "CRITICAL_UPDATES": "Updates required",
        }
        i3status_data = {
            "icon": "archive",
            "state": i3status_state_map[state.text_value.name],
            "text": i3status_text_map[state.text_value.name],
        }
        return json.dumps(i3status_data), {}
