import functools
import datetime
from collections import defaultdict
from typing import Dict, List, Set, Optional, Iterable

from AU2.database.model import Event, Assassin
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.date_utils import dt_to_timestamp, get_now_dt
# TODO: from ??? import calculate_formula


class ScoreManager:
    def __init__(self,
                 assassin_ids: Iterable[str],
                 formula: str = "",
                 bonuses: Dict[str, int] = {},
                 perma_death=True,
                 game_end: Optional[datetime.datetime] = None):
        self.kill_tree: Dict[str, List[str]] = defaultdict(list)
        self.attempt_counter: Dict[str, int] = {}
        self.live_assassins = set(assassin_ids)
        self.formula = formula
        self.bonuses = bonuses
        self.perma_death = perma_death
        self.game_end = game_end
        self.death_manager = DeathManager()

    def add_event(self, e: Event):
        # adding an event invalidates the cache
        self._score.cache_clear()
        self.death_manager.add_event(e)
        for (killer, victim) in e.kills:
            # in regular games, live_assassins will initially only include non-police,
            # and dead players will be pruned as events are added
            if victim not in self.live_assassins:
                continue
            self.kill_tree[killer].append(victim)
            if self.perma_death:
                self.live_assassins.discard(victim)
        for assassin_id in e.pluginState.get("CompetencyPlugin", {}).get("attempts", []):
            self.attempt_counter[assassin_id] = self.attempt_counter.get(assassin_id, 0) + 1

    def _conkers(self, identifier: str, visited: Optional[Set[str]] = None) -> int:
        if visited is None: # need to do this because we mutate visited
            visited = set()
        # prevent the same player giving conkers twice via different paths through the kill tree
        # (and also deals with loops. note that players can't get conkers from themselves;
        # we may wish to change this for a "revenge bonus")
        # both of these should only happen without perma-death
        if identifier in visited:
            return -1  # cancels out the `1 +` in this term of the sum
        else:
            visited.add(identifier)
        return sum((1 + self._conkers(v, visited) for v in self.kill_tree.get(identifier, [])))

    def _kills(self, identifier: str) -> int:
        return len(self.kill_tree[identifier])

    def _attempts(self, identifier: str) -> int:
        return self.attempt_counter.get(identifier, 0)

    def _bonus(self, identifier: str) -> float:
        return self.bonuses.get(identifier, 0)

    @functools.cache
    def _score(self, identifier: str) -> float:
        # placeholder!
        # TODO: should use Jamie's formula parser to calculate score
        k = self._kills(identifier)
        c = self._conkers(identifier)
        b = self._bonus(identifier)
        a = self._attempts(identifier)
        import math
        score = eval(self.formula) if self.formula else c
        return score

    def get_score(self, a: Assassin) -> float:
        return self._score(a.identifier)

    # used for stats page
    def get_conkers(self, a: Assassin) -> int:
        return self._conkers(a.identifier)

    def get_kills(self, a: Assassin) -> int:
        return self._kills(a.identifier)

    def get_attempts(self, a: Assassin) -> int:
        return self._attempts(a.identifier)

    def get_death_events(self, a: Assassin) -> List:
        return self.death_manager.get_death_events(a)

    def get_rating(self, a: Assassin) -> float:
        """
        'Rating' is used for the AU1-style ordering of players.
        Under this ordering, players are ranked by their time of death.
        However, to prevent duellists being ranked below non-duellists,
        all players who survived open season are instead ranked according to score.
        This is achieved by assigning a 'rating' to each player,
        which for players who died before the end of open season is just the timestamp of their death,
        but for players who survived open season,
        a player's rating is the timestamp of the end of open season plus that player's score.
        """
        game_end = self.game_end or get_now_dt()
        deaths = self.deaths[a.identifier]
        if deaths and (game_end is None or deaths[-1].datetime < game_end):
            return dt_to_timestamp(deaths[-1].datetime)
        else:
            return dt_to_timestamp(game_end) + self._score(a.identifier)
