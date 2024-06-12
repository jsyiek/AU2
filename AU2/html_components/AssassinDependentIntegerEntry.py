import datetime
from html import escape
from typing import List, Tuple, Dict

from AU2.html_components import HTMLComponent


class AssassinDependentIntegerEntry(HTMLComponent):
    name: str = "AssassinDependentIntegerEntry"

    def __init__(self, pseudonym_list_identifier: str, identifier: str, title: str, default: Dict[str, int]={}):
        self.pseudonym_list_identifier = pseudonym_list_identifier
        self.title = title
        self.identifier = identifier
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
