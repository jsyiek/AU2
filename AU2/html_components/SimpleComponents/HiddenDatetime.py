import datetime

from AU2.html_components.HiddenComponent import HiddenComponent
from AU2.plugins.util.date_utils import dt_to_timestamp


class HiddenDatetime(HiddenComponent[datetime.datetime]):
    name: str = "HiddenDatetime"

    def _representation(self) -> str:
        return f"""
            <input type="hidden" id="{self.identifier}" value="{dt_to_timestamp(self.default)}">
        """
