from dataclasses import dataclass, field

import datetime as dt
from dataclasses_json import dataclass_json, config
from typing import Any, Dict, Tuple, List

from AU2 import TIMEZONE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import PersistentFile


@dataclass_json
@dataclass
class Event(PersistentFile):
    """ Represents an event """

    # All assassins are referred to by their `identifier`.

    # map from assassin ID to index of pseudonym in their pseudonym list
    assassins: Dict[str, int]

    # time the event occurred
    datetime: dt.datetime = field(
        metadata=config(
            encoder=lambda ts: ts.replace(tzinfo=TIMEZONE).timestamp(),
            decoder=lambda ts: TIMEZONE.localize(dt.datetime.fromtimestamp(ts))
        )
    )

    # headline of the event
    headline: str

    # from assassin ID and their pseudonym ID to their report
    reports: List[Tuple[str, int, str]]

    # Map from killer to victim
    kills: List[Tuple[str, str]]

    # to allow plugins to make notes on the event
    pluginState: Dict[str, Any] = field(default_factory=dict)

    # Human-readable identifier for the event
    identifier: str = ""
    __secret_id: str = ""

    def __post_init__(self):
        if not self.__secret_id:
            self.__secret_id = GENERIC_STATE_DATABASE.get_unique_str()
        if not self.identifier:
            self.identifier = "(" + self.__secret_id + ") " + self.headline[0:25].rstrip()

        self.datetime = self.datetime.replace(tzinfo=None)
