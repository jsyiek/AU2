from html import escape
from typing import List, Tuple, Dict

from AU2.html_components import HTMLComponent


class AssassinPseudonymPair(HTMLComponent):
    name: str = "AssassinPseudonymPair"

    def __init__(self, identifier: str, title: str, assassins: List[Tuple[str, List[str]]], default: Dict[str, int]={}):
        self.title = escape(title)
        self.identifier = escape(identifier)
        self.uniqueStr = self.get_unique_str()
        self.assassins = assassins
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
