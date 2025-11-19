import os
from dataclasses import dataclass
from typing import Dict, Optional

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

    def get(self, identifier: str) -> Optional[Event]:
        """
        Fetches an event given an identifier, if it exists, otherwise returns None
        """
        return self.events.get(identifier, None)

    def _refresh(self):
        """
        Forces a refresh of the underlying database
        """
        if self.TEST_MODE:
            self.events = {}
            return

        self.events = self.load().events

EVENTS_DATABASE = EventsDatabase.load()
