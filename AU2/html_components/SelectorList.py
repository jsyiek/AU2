from html import escape
from typing import List

from AU2.html_components import HTMLComponent


class SelectorList(HTMLComponent):
    name: str = "SelectorList"

    def __init__(self, identifier: str, title: str, options: List[str], defaults: List[str] = []):
        self.title = escape(title)
        self.identifier = escape(identifier)
        self.uniqueStr = self.get_unique_str()
        self.options = [a for a in options]
        self.defaults = defaults
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
