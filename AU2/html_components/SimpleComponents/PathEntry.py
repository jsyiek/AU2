from html import escape
from typing import List

from AU2.html_components import HTMLComponent


class PathEntry(HTMLComponent):
    name: str = "PathEntry"

    def __init__(self, identifier: str, title: str, default: str = None):
        self.identifier = identifier
        self.title = title
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
