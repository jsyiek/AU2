from html import escape
from typing import List, Tuple

from AU2.html_components import HTMLComponent


class KillAdd(HTMLComponent):
    name: str = "KillAdd"

    def __init__(self, assassins_list_identifier: str, identifier: str, title: str, default: List[Tuple[str, str]]=[]):
        self.assassins_list_identifier = escape(assassins_list_identifier)
        self.title = escape(title)
        self.identifier = escape(identifier)
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
