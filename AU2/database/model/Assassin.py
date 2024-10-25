from dataclasses_json import dataclass_json
from typing import List, Dict, Any

from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model.PersistentFile import PersistentFile
from dataclasses import dataclass, field


@dataclass_json
@dataclass
class Assassin(PersistentFile):
    """ Class for keeping track of an assassin """
    pseudonyms: List[str]
    real_name: str
    pronouns: str
    email: str
    address: str
    water_status: str
    college: str
    notes: str
    is_police: bool
    # almost everything that is stateful is probably best placed in an event
    # but for a few plugins, it might make sense to place the information directly onto the assassin
    # make sure you know what you're doing (modifications here can't be undone with a later event state change)
    plugin_state: Dict[str, Any] = field(default_factory=dict)
    identifier: str = ""   # human-readable unique identifier
    _secret_id: str = ""  # unique identifier

    def __post_init__(self):
        if len(self.pseudonyms) == 0:
            raise ValueError(f"Tried to initialize {self}, but no pseudonyms were provided!")
        if not self._secret_id:
            self._secret_id = GENERIC_STATE_DATABASE.get_unique_str()

        if self.TEST_MODE:
            self.identifier = f"{self.real_name} identifier"
            return

        # Don't move this out of __post_init__
        if not self.identifier:
            dotdotdot = "..." if len(self.pseudonyms[0]) > 15 else ""
            self.identifier = f"{self.real_name} ({self.pseudonyms[0][:15]}{dotdotdot}) ID: {self._secret_id}"

    def get_pseudonym(self, i: int) -> str:
        if i >= len(self.pseudonyms):
            return self.pseudonyms[-1]
        return self.pseudonyms[i]

    def all_pseudonyms(self) -> str:
        return " AKA ".join(self.pseudonyms)
