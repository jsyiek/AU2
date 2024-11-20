import datetime
from typing import Optional

from AU2.html_components import HTMLComponent
from AU2.plugins.util.date_utils import get_now_dt


class OptionalDatetimeEntry(HTMLComponent):
    """Similar to DatetimeEntry but allows blank values"""
    name: str = "OptionalDatetimeEntry"

    def __init__(self, identifier: str, title: str, default: Optional[datetime.datetime] = None):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
