from html import escape
from typing import List, Tuple

from AU2.html_components import HTMLComponent


class KillDependentSelector(HTMLComponent):
    name: str = "KillDependentSelector"

    def __init__(self, kills_identifier: str, identifier: str, title: str, default: List[Tuple[str, str]]=[]):
        self.kills_identifier = escape(kills_identifier)
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
