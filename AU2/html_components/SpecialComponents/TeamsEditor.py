from html import escape
from typing import Sequence
from AU2.html_components import HTMLComponent

class TeamsEditor(HTMLComponent):
    """
    Special component for setting teams for the purpose of targeting.
    """
    name: str = "TeamsEditor"

    def __init__(self, identifier: str, title: str, assassins: Sequence[str], values: Sequence[str]):
        self.identifier = escape(identifier)
        self.title = escape(title)
        self.assassins = assassins
        self.uniqueStr = self.get_unique_str()
        self.values = [a for a in values]
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
