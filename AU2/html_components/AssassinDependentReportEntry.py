from html import escape
from typing import List, Tuple, Dict

from AU2.html_components import HTMLComponent


class AssassinDependentReportEntry(HTMLComponent):
    name: str = "AssassinDependentReportEntry"

    def __init__(self, pseudonym_list_identifier: str, identifier: str, title: str, default: List[Tuple[str, int, str]]=[]):
        self.pseudonym_list_identifier = pseudonym_list_identifier
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
