import json

from typing import Union

from AU2.html_components import HTMLComponent


class HiddenJSON(HTMLComponent):
    name: str = "HiddenJSON"
    noInteraction: bool = True

    def __init__(self, identifier: str, default: Union[dict, list]):
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        escaped_encoded = json.dumps(self.default).replace(r'"', r'\"')
        return f"""
            <input type="hidden" id="{self.identifier}" value="{escaped_encoded}">
        """
