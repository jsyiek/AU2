from html import escape
from typing import Tuple, List

from AU2.html_components import HTMLComponent


class AssassinDependentTransferEntry(HTMLComponent):
    name: str = "Transfer"

    def __init__(self, assassins_list_identifier: str, owners: List[str], identifier: str, title: str, default: List[Tuple[str, str]]=[]):
        self.assassins_list_identifier = escape(assassins_list_identifier)
        self.title = title
        self.owners = owners
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
