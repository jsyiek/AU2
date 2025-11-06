import datetime

from AU2.html_components import HTMLComponent
from AU2.plugins.util.date_utils import dt_to_timestamp


class HiddenDatetime(HTMLComponent):
    name: str = "HiddenDatetime"
    noInteraction: bool = True

    def __init__(self, identifier: str, default: datetime.datetime):
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        return f"""
            <input type="hidden" id="{self.identifier}" value="{dt_to_timestamp(self.default)}">
        """
