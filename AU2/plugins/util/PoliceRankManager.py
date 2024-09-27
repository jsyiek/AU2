import datetime

from collections import defaultdict

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin

DEFAULT_RANKS = {
    '0': 'Police -2',
    '1': 'Police -1',
    '2': 'Police',  # Default police rank
    '3': 'Police +1',
    '4': 'Police +2',
    '5': 'Police +3',
    '6': 'Police +4',
    '7': 'Police +5',
    '8': 'Police +6',
    '9': 'Umpire',
}
DEFAULT_POLICE_RANK = '2'


class PoliceRankManager:
    """
    Simple manager for police ranks
    """

    def __init__(self):
        # from assassin ID to deadline
        self.assassin_ranks = defaultdict(lambda: DEFAULT_POLICE_RANK)
        self.activated = GENERIC_STATE_DATABASE.plugin_map.get("PolicePlugin", False)

    def add_event(self, e: Event):
        for (aID, rank) in e.pluginState.get("PolicePlugin", {}).get("rank", {}).items():
            self.assassin_ranks[aID] = rank

    def get_rank(self, a: Assassin):
        return self.assassin_ranks[a.identifier]
