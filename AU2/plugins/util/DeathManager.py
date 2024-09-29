from collections import defaultdict

from AU2.database.model import Event, Assassin


class DeathManager:
    def __init__(self, perma_death: bool=True):
        self.perma_death = perma_death
        self.deaths = []
        self.death_timings = defaultdict(lambda: [])

    def add_event(self, e: Event):
        if not self.perma_death:
            self.deaths = []
        for (killer, victim) in e.kills:
            self.deaths.append(victim)
            self.death_timings[victim].append(e.datetime)

    def get_dead(self):
        return self.deaths

    def get_death_timings(self, a: Assassin):
        return self.death_timings[a.identifier]

    def is_dead(self, a: Assassin):
        return a.identifier in self.deaths
