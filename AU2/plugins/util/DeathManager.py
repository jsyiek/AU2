from collections import defaultdict

from AU2.database.model import Event, Assassin


class DeathManager:
    def __init__(self, perma_death: bool=True):
        self.perma_death = perma_death
        self.deaths = []

    def add_event(self, e: Event):
        if not self.perma_death:
            self.deaths = []
        for (killer, victim) in e.kills:
            self.deaths.append(victim)

    def get_dead(self):
        return self.deaths

    def is_dead(self, a: Assassin):
        return a.identifier in self.deaths
