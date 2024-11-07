import os

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Dict, List

from AU2 import BASE_WRITE_LOCATION
from AU2.database.model import PersistentFile, Assassin


@dataclass_json
@dataclass
class AssassinsDatabase(PersistentFile):
    WRITE_LOCATION = os.path.join(BASE_WRITE_LOCATION, "AssassinsDatabase.json")
    assassins: Dict[str, Assassin]

    def add(self, assassin: Assassin):
        """
        Adds an assassin to the database.

        Parameters:
            assassin:  Assassin to add
        """
        self.assassins[assassin.identifier] = assassin

    def delete(self, assassin: Assassin):
        """
        Removes an assassin from the database.

        Parameters:
            assassin: Assassin to delete (uses ID)
        """
        del self.assassins[assassin.identifier]

    def get(self, identifier: str) -> Assassin:
        """
        Returns an Assassin object associated with an identifier

        Parameters:
            identifier: Identifier of assassin

        Returns:
            assassin object
        """
        return self.assassins[identifier]

    def get_identifiers(self) -> List[str]:
        """
        Returns:
            list of identifiers sorted alphabetically
        """
        return sorted([v for v in self.assassins], key=lambda n: n.lower())

    def _refresh(self):
        """
        Forces a refresh of the underlying database
        """
        if self.TEST_MODE:
            self.assassins = {}
            return

        self.assassins = self.load().assassins


ASSASSINS_DATABASE = AssassinsDatabase.load()
