from typing import List

from AU2.html_components import HTMLComponent


class EmailSelector(HTMLComponent):
    name: str = "EmailSelector"

    def __init__(self, identifier: str, assassins: List[str], alive_assassins: List[str], police_assassins: List[str]):
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.assassins = assassins
        self.alive_assassins = alive_assassins
        self.police_assassins = police_assassins
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
