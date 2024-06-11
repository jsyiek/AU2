import os
from dataclasses import dataclass
from typing import Dict

from dataclasses_json import dataclass_json

from AU2.database import BASE_WRITE_LOCATION
from AU2.database.model import PersistentFile, Event


@dataclass_json
@dataclass
class EventsDatabase(PersistentFile):
    WRITE_LOCATION = os.path.join(BASE_WRITE_LOCATION, "EventsSummary.json")

    # map from identifier to event
    events: Dict[str, Event]

    def add(self, event: Event):
        """
        Adds an event to the database
        """
        self.events[event.identifier] = event

    def get(self, identifier: str):
        """
        Fetches an event given an identifier
        """
        return self.events[identifier]

EVENTS_DATABASE = EventsDatabase.load()
