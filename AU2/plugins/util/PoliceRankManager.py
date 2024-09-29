from collections import defaultdict

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin

DEFAULT_RANKS = [
    'Bog-standard Constable',  # Default police rank
    'Chief of Police',
    'Umpire',
]
DEFAULT_POLICE_RANK = 0
AUTO_RANK_DEFAULT = True
MANUAL_RANK_DEFAULT = False
POLICE_KILLS_RANKUP_DEFAULT = True


class PoliceRankManager:
    """
    Simple manager for police ranks
    """

    def __init__(self, auto_ranking, police_kill_ranking):
        self.assassin_relative_ranks = defaultdict(lambda: 0)
        self.activated = GENERIC_STATE_DATABASE.plugin_map.get("PolicePlugin", False)
        self.auto_ranking = auto_ranking
        self.police_kill_ranking = police_kill_ranking

    def add_event(self, e: Event):
        for (aID, rank) in e.pluginState.get("PolicePlugin", {}).items():
            self.assassin_relative_ranks[aID] += rank
        if self.auto_ranking:
            for (killer, victim) in e.kills:
                if ASSASSINS_DATABASE.get(killer).is_police:
                    if self.police_kill_ranking:
                        self.assassin_relative_ranks[killer] += 1
                    elif not ASSASSINS_DATABASE.get(victim).is_police:
                        self.assassin_relative_ranks[killer] += 1

    def get_min_rank(self):
        try:
            return min(self.assassin_relative_ranks.values())
        except ValueError:
            return 0

    def get_max_rank(self):
        try:
            return max(self.assassin_relative_ranks.values())
        except ValueError:
            return 0

    def get_relative_rank(self, a: Assassin):
        return self.assassin_relative_ranks[a.identifier]
