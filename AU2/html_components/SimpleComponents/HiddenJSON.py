import json
from typing import Union
from AU2.html_components.HiddenComponent import HiddenComponent


class HiddenJSON(HiddenComponent[Union[dict, list]]):
    name: str = "HiddenJSON"

    def _representation(self) -> str:
        return f"""
            <input type="hidden" id="{self.identifier}" value="{json.dumps(self.default)}">
        """
