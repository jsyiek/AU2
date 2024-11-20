import functools
from collections import defaultdict
from typing import Dict, List, Set, Optional

from AU2.database.model import Event, Assassin
# TODO: from ??? import calculate_formula


class ScoreManager:
    def __init__(self,
                 assassin_ids: List[str],
                 formula: str = "",
                 bonuses: Dict[str, int] = {},
                 perma_death=True):
        self.kill_tree: Dict[str, List[str]] = {}
        self.attempt_counter: Dict[str, int] = {}
        self.live_assassins = set(assassin_ids)
        self.formula = formula
        self.bonuses = bonuses
        self.perma_death = perma_death

    def add_event(self, e: Event):
        # adding an event invalidates the cache
        self._score.cache_clear()
        for (killer, victim) in e.kills:
            # in regular games, live_assassins will initially only include non-police,
            # and dead players will be pruned as events are added
            if victim not in self.live_assassins:
                continue
            self.kill_tree.setdefault(killer, []).append(victim)
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
        # both of these should only happen without perma-deat
        if identifier in visited:
            return -1  # cancels out the `1 +` in this term of the sum
        else:
            visited.add(identifier)
        return sum((1 + self._conkers(v, visited) for v in self.kill_tree.get(identifier, [])))

    def _kills(self, identifier: str) -> int:
        return len(self.kill_tree.get(identifier, []))

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
        score = eval(self.formula)
        return score

    def get_score(self, a: Assassin) -> float:
        return self._score(a.identifier)