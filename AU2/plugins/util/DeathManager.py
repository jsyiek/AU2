from collections import defaultdict
from typing import List, Dict

from AU2.database.model import Event, Assassin


class DeathManager:
    def __init__(self):
        self.deaths: Dict[str, List[Event]] = defaultdict(list)

    def add_event(self, e: Event):
        event_deaths = set()
        for (killer, victim) in e.kills:
            if victim not in event_deaths:
                self.deaths[victim].append(e)
                event_deaths.add(victim)

    def get_dead(self) -> List[str]:
        return list(self.deaths)

    def is_dead(self, a: Assassin) -> bool:
        return a.identifier in self.deaths

    def get_death_events(self, a: Assassin) -> List:
        return self.deaths[a.identifier]
