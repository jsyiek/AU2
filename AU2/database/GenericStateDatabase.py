import os
from dataclasses import dataclass

from dataclasses_json import dataclass_json

from AU2.database import BASE_WRITE_LOCATION
from AU2.database.model.PersistentFile import PersistentFile


@dataclass_json
@dataclass
class GenericStateDatabase(PersistentFile):
    """
    This class is for state that is generic and reusable between files.
    Not much should go here, but you may find the utility methods useful.
    """
    uniqueId: int = 0  # see get_unique_str
    WRITE_LOCATION = os.path.join(BASE_WRITE_LOCATION, "GenericState.json")

    @classmethod
    def get_unique_str(cls) -> str:
        """
        Returns a game-wide unique string ID.
        Auto-incrementing integer.
        :return: unique ID as a string.
        """
        t = cls.uniqueId
        cls.uniqueId += 1
        return str(t)


GENERIC_STATE_DATABASE = GenericStateDatabase.load()
