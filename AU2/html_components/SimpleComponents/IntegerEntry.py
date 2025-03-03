from typing import Optional

from AU2.html_components import HTMLComponent


class IntegerEntry(HTMLComponent):
    name: str = "IntegerEntry"

    def __init__(self, identifier: str, title: str, default: Optional[int] = None):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
