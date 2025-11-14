import json

from typing import Union

from AU2.html_components.HiddenComponent import HiddenComponent


class HiddenJSON(HiddenComponent[Union[dict, list]]):
    name: str = "HiddenJSON"

    def _representation(self) -> str:
        escaped_encoded = json.dumps(self.default).replace(r'"', r'\"')
        return f"""
            <input type="hidden" id="{self.identifier}" value="{escaped_encoded}">
        """
