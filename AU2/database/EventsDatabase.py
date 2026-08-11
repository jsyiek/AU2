import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from dataclasses_json import dataclass_json

from AU2.database import BASE_WRITE_LOCATION
from AU2.database.model import PersistentFile, Event


@dataclass_json
@dataclass
class EventsDatabase(PersistentFile):
    WRITE_LOCATION = BASE_WRITE_LOCATION / "EventsSummary.json"

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

    def events_chronologically(self, last: Optional[Event] = None) -> List[Event]:
        """
        Returns events in chronological order.

        Args:
            last (Optional[Event]): The last event to return. If `None`, all events will be returned.
        """
        events_up_to_cutoff = (
            (e for e in self.events.values()
             if e.datetime < last.datetime or (e.datetime == last.datetime and e.get_numerical_id() <= last.get_numerical_id()))
        ) if last else self.events.values()
        return sorted(events_up_to_cutoff, key=lambda e: (e.datetime, e.get_numerical_id()))

    def _refresh(self):
        """
        Forces a refresh of the underlying database
        """
        if self.TEST_MODE:
            self.events = {}
            return

        self.events = self.load().events

EVENTS_DATABASE = EventsDatabase.load()
