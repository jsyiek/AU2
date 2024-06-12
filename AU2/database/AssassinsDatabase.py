import os

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Dict

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

        :param assassin:  Assassin to add
        """
        self.assassins[assassin.identifier] = assassin

    def delete(self, assassin: Assassin):
        """
        Removes an assassin from the database.

        :param assassin: Assassin to delete (uses ID)
        """
        del self.assassins[assassin.identifier]

    def get(self, identifier: str):
        return self.assassins[identifier]

    def _refresh(self):
        """
        Forces a refresh of the underlying database
        """
        self.assassins = self.load().assassins


ASSASSINS_DATABASE = AssassinsDatabase.load()
