import datetime
from html import escape

from AU2.html_components import HTMLComponent


class DatetimeEntry(HTMLComponent):
    name: str = "DatetimeEntry"

    def __init__(self, identifier: str, title: str, default: datetime.datetime=datetime.datetime.now()):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
