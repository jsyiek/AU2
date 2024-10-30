import datetime
from html import escape

from AU2 import TIMEZONE
from AU2.html_components import HTMLComponent
from AU2.plugins.util.date_utils import get_now_dt


class DatetimeEntry(HTMLComponent):
    name: str = "DatetimeEntry"

    def __init__(self, identifier: str, title: str, default: datetime.datetime=get_now_dt()):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
