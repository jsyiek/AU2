import os
from dataclasses import dataclass
from dataclasses_json import dataclass_json

from AU2.database import BASE_WRITE_LOCATION


@dataclass_json
class PersistentFile:
    WRITE_LOCATION = ""

    def __hash__(self):
        return hash(self.get_id())

    def save(self):
        dump = self.to_json()
        with open(self.WRITE_LOCATION, "w+") as F:
            F.write(dump)

    @classmethod
    def load(cls):
        with open(cls.WRITE_LOCATION, "r") as F:
            dump = F.read()
        return cls.from_json(dump)


@dataclass_json
@dataclass
class GenericStateDatabase:
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
