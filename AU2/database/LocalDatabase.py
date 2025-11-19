import os
from dataclasses import dataclass, field
from typing import Dict, Any

from dataclasses_json import dataclass_json

from AU2.database import BASE_WRITE_LOCATION
from AU2.database.model.PersistentFile import PersistentFile


@dataclass_json
@dataclass
class LocalDatabase(PersistentFile):
    """
    This class is for storing local settings that shouldn't be uploaded to SRCF or saved in backups
    """
    arb_state: Dict[str, Any] = field(default_factory=dict)

    # __ signals that the database file shouldn't be uploaded
    WRITE_LOCATION = os.path.join(BASE_WRITE_LOCATION, "__LocalDatabase.json")

    def _refresh(self):
        """
        Forces a refresh of underlying state
        """
        loaded = self.load()
        self.arb_state = loaded.arb_state


LOCAL_DATABASE = LocalDatabase()
