import os

from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Callable, Dict, Iterable, List, Tuple, Union

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
                     include_hidden: Union[Callable[[Assassin], bool], bool] = False,
                     key=lambda a: a.real_name.lower()) -> List[Assassin]:
        """
        Parameters:
            include: function that takes a non-hidden assassin and returns whether it should be included in the
                returned list. Defaults to always return True.
            include_hidden: either
                - A boolean indicating whether hidden assassins should be returned (if True, the same criteria as for
                    non-hidden assassins are applied for inclusion, if False, no hidden assassins are returned)
                - Or a function that takes a hidden Assassin object and returns whether it should be include in the
                returned list.
            key: a 'key' function of the kind used in `List.sort()`. Defaults to sorting by real name.

        Returns:
            list of non-hidden assassins (as Assassin objects) satisfying `include`, and hidden assassins satisfying
                include_hidden, sorted according to `key`
        """
        if isinstance(include_hidden, bool):
            include_hidden = include if include_hidden else lambda x: False
        out = [a for a in self.assassins.values() if (a.hidden and include_hidden(a)) or (not a.hidden and include(a))]
        out.sort(key=key)
        return out

    def get_identifiers(self, *,
                        include: Callable[[Assassin], bool] = lambda x: True,
                        include_hidden: Union[Callable[[Assassin], bool], bool] = False,
                        key=lambda a: a.identifier.lower()) -> List[str]:
        """
        Parameters: same as `get_filtered`

        Returns:
            list of identifiers of assassins filtered according to the `include` and `include_hidden` functions and
                ordered according to `key`
        """
        return [a.identifier for a in self.get_filtered(include=include, include_hidden=include_hidden, key=key)]

    def idents_to_disp_ident_pairs(self, idents: Iterable[str]) -> List[Tuple[str, str]]:
        return [(self.get(ident).display_name(), ident) for ident in idents]

    def get_display_name_ident_pairs(self, *,
                        include: Callable[[Assassin], bool] = lambda x: True,
                        include_hidden: Union[Callable[[Assassin], bool], bool] = False,
                        key=lambda a: a.real_name.lower()) -> List[Tuple[str, str]]:
        """
        Parameters: same as `get_filtered`

        Returns:
            list of pairs (display name, identifier), filtered according to the `include` and `include_hidden` functions,
                sorted according to `key`
        """
        return [(a.display_name(), a.identifier) for a in self.get_filtered(include=include, include_hidden=include_hidden, key=key)]

    def get_ident_pseudonym_pairs(self, *,
                     include: Callable[[Assassin], bool] = lambda x: True,
                     include_hidden: Union[Callable[[Assassin], bool], bool] = False,
                     key=lambda a: a.real_name.lower()) -> List[Tuple[str, List[str]]]:
        """
        Parameters: same as `get_filtered`

        Returns:
            list of pairs (identifier, list of pseudonyms) filtered according to the `include` and `include_hidden`
            functions, sorted according to `key`
        """
        return [
            (a.identifier, a.pseudonyms) for a in self.get_filtered(
                include=include,
                include_hidden=include_hidden,
                key=key
            )
        ]

    def _refresh(self):
        """
        Forces a refresh of the underlying database
        """
        if self.TEST_MODE:
            self.assassins = {}
            return

        self.assassins = self.load().assassins


ASSASSINS_DATABASE = AssassinsDatabase.load()
