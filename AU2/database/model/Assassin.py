from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Dict, List

from AU2.database import ASSASSINS_WRITE_LOCATION
from AU2.database.database import GENERIC_STATE_DATABASE
from AU2.database.model.PersistentFile import PersistentFile


@dataclass_json
@dataclass
class Assassin(PersistentFile):
    """ Class for keeping track of an assassin """
    pseudonyms: List[str]
    real_name: str
    email: str
    address: str
    water_status: str
    college: str
    notes: str
    is_police: bool
    identifier: str = ""   # human-readable unique identifier
    __secret_id: str = ""  # unique identifier

    def __post_init__(self):
        if len(self.pseudonyms) == 0:
            raise ValueError(f"Tried to initialize {self}, but no pseudonyms were provided!")
        self._secret_id = GENERIC_STATE_DATABASE.get_unique_str()
        # Don't move this out of __post_init__
        if not self.identifier:

            self.identifier = f"{self.real_name} ({self.pseudonyms[0]}) ID: {self._secret_id}"

    def get_pseudonym(self, i: int) -> str:
        if i >= len(self.pseudonyms):
            return self.pseudonyms[-1]
        return self.pseudonyms[i]


@dataclass_json
@dataclass
class AssassinsDatabase(PersistentFile):
    assassins: Dict[str, Assassin]

    def add(self, assassin: Assassin):
        """
        Adds an assassin to the database.

        :param assassin:  Assassin to add
        """
        self.assassins[assassin.identifier] = assassin
