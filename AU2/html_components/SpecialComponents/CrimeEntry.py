from typing import Tuple, Optional

from AU2.html_components import HTMLComponent


class CrimeEntry(HTMLComponent):
    """
    Special component for entering details about a player going Wanted.
    This is needed because of the special behaviour when entering a value <= 0 for the wanted duration.
    """
    name: str = "CrimeEntry"

    def __init__(self, identifier: str, assassin_identifier: str, default: Tuple[Optional[int], str, str]):
        self.identifier = identifier
        self.assassin_identifier = assassin_identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
