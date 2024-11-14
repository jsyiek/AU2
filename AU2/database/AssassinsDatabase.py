import os

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Dict, List, Callable, Tuple, Optional

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

    def get_filtered(self, *,
                     include: Callable[[Assassin], bool] = lambda x: True,
                     include_hidden: Callable[[Assassin], bool] = lambda x: False) -> List[Assassin]:
        """
        Parameters:
            include: function that takes a non-hidden assassin and returns whether it should be included in the
                returned list. Defaults to always return True.
            include_hidden: function that takes a hidden Assassin object and returns whether it should be include in the
                returned list. Defaults to always return False.

        Returns:
            list of non-hidden assassins (as Assassin objects) satisfying `include`, and hidden assassins satisfying
                include_hidden
        """
        return [a for a in self.assassins.values() if (a.hidden and include_hidden(a)) or (not a.hidden and include(a))]

    def get_identifiers(self, *,
                     include: Callable[[Assassin], bool] = lambda x: True,
                     include_hidden: Callable[[Assassin], bool] = lambda x: False) -> List[str]:
        """
        Parameters:
            include: function that takes a non-hidden assassin and returns whether it should be included in the
                returned list. Defaults to always return True.
            include_hidden: function that takes a hidden Assassin object and returns whether it should be include in the
                returned list. Defaults to always return False.
        Returns:
            list of identifiers sorted alphabetically, filtered according to the `include` and `include_hidden` functions
        """
        return sorted([a.identifier for a in self.get_filtered(include=include, include_hidden=include_hidden)],
                      key=lambda x: x.lower())

    def get_ident_pseudonym_pairs(self, *,
                     include: Callable[[Assassin], bool] = lambda x: True,
                     include_hidden: Callable[[Assassin], bool] = lambda x: False) -> List[Tuple[str, List[str]]]:
        """
        Parameters:
            include: function that takes a non-hidden assassin and returns whether it should be included in the
                returned list. Defaults to always return True.
            include_hidden: function that takes a hidden Assassin object and returns whether it should be include in the
                returned list. Defaults to always return False.
        Returns:
            list of identifiers sorted alphabetically, filtered according to the `include` and `include_hidden` functions
        """
        return sorted([
            (a.identifier, a.pseudonyms) for a in self.get_filtered(
                include=include,
                include_hidden=include_hidden
            )
        ])

    def _refresh(self):
        """
        Forces a refresh of the underlying database
        """
        if self.TEST_MODE:
            self.assassins = {}
            return

        self.assassins = self.load().assassins


ASSASSINS_DATABASE = AssassinsDatabase.load()
