import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

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

    last_uploaded: Optional[int] = None

    # map from plugin identifier to whether it is enabled
    plugin_map: Dict[str, bool] = field(default_factory=dict)

    # arbitrary state dictionaries
    # plugins can leave config parameters here
    arb_state: Dict[str, Any] = field(default_factory=dict)
    arb_int_state: Dict[str, int] = field(default_factory=dict)

    WRITE_LOCATION = BASE_WRITE_LOCATION / "GenericState.json"

    def __post_init__(self):
        if not isinstance(self.uniqueId, int):
            self.uniqueId = 0

    def get_unique_str(self) -> str:
        """
        Returns a game-wide unique string ID.
        Auto-incrementing integer.
        :return: unique ID as a string.
        """
        t = self.uniqueId
        self.uniqueId += 1
        return str(t)

    def _refresh(self):
        """
        Forces a refresh of underlying state
        """
        loaded = self.load()
        if self.TEST_MODE:
            self.arb_state = {}
            self.arb_int_state = {}
            return

        self.uniqueId = loaded.uniqueId
        self.plugin_map = loaded.plugin_map
        self.arb_state = loaded.arb_state
        self.arb_int_state = loaded.arb_int_state


GENERIC_STATE_DATABASE = GenericStateDatabase.load()
