import datetime
from html import escape
from typing import List, Tuple, Dict

from AU2.html_components import HTMLComponent


class AssassinDependentCrimeEntry(HTMLComponent):
    name: str = "AssassinDependentCrimeEntry"

    def __init__(self, pseudonym_list_identifier: str, identifier: str, title: str, default: Dict[str, Tuple[int, str, str]]):
        self.pseudonym_list_identifier = pseudonym_list_identifier
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
