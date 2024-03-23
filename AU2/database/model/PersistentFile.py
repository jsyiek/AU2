from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
class PersistentFile:
    def __hash__(self):
        return hash(self.get_id())


@dataclass_json
@dataclass
class GenericStateDatabase:
    """
    This class is for state that is generic and reusable between files.
    Not much should go here, but you may find the utility methods useful.
    """
    uniqueId: int = 0  # see get_unique_str

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
