from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Any, Dict, List

from AU2.database.database import GENERIC_STATE_DATABASE
from AU2.database.model import Assassin, PersistentFile


@dataclass_json
@dataclass
class Event(PersistentFile):
    """ Represents an event """

    # All assassins are referred to by their `identifier`.

    # map from assassin ID to index of pseudonym in their pseudonym list
    assassins: Dict[str, int]

    headline: str

    # from assassin to their report
    reports: List[Dict[str, str]]

    # Map from victim to killer
    kills: List[Dict[str, str]]

    # Coloring of name in headline, specified as hex
    assassin_colors: Dict[str, hex]

    # to allow plugins to make notes on the event
    pluginState: Dict[str, Any]

    # Human-readable identifier for the event
    identifier: str = ""

    def __post_init__(self):
        if not self.identifier:
            identifier = GENERIC_STATE_DATABASE.get_unique_str()


@dataclass_json
@dataclass
class EventsDatabase(PersistentFile):
    # map from identifier to event
    events: Dict[str, Event]