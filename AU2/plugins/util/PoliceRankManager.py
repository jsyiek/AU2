from collections import defaultdict

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin
from AU2.html_components.Label import Label

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

    def get_relative_rank(self, player_id: str):
        return self.assassin_relative_ranks[player_id]

    def get_rank_name(self, player_id: str):
        return GENERIC_STATE_DATABASE.arb_state.get("PolicePlugin", {}).get("PolicePlugin_ranks", DEFAULT_RANKS)[
            self.get_relative_rank(player_id)
            + int(GENERIC_STATE_DATABASE.arb_state.get("PolicePlugin", {}).get("PolicePlugin_default_rank", DEFAULT_POLICE_RANK))
        ]

    def generate_new_ranks_if_necessary(self):
        # Code to generate new ranks if police are promoted/demoted more than ever before
        # This will add them to the database to be renamed by the umpire
        message = []
        default_rank = int(GENERIC_STATE_DATABASE.arb_state.get("PolicePlugin", {}).get("PolicePlugin_default_rank", DEFAULT_POLICE_RANK))
        rank_list = GENERIC_STATE_DATABASE.arb_state.get("PolicePlugin", {}).get("PolicePlugin_ranks", DEFAULT_RANKS)
        if self.get_min_rank() < -default_rank:
            current_ranks = rank_list
            current_default = default_rank
            for i in range(-current_default - self.get_min_rank()):
                current_ranks.insert(0, f"Level {-(i + current_default + 1)} Constable")
            rank_list = current_ranks
            default_rank = -self.get_min_rank()
            GENERIC_STATE_DATABASE.arb_state.setdefault("PolicePlugin", {})["PolicePlugin_ranks"] = rank_list
            GENERIC_STATE_DATABASE.arb_state.setdefault("PolicePlugin", {})["PolicePlugin_default_rank"] = default_rank
            message.append(Label("[POLICE] Warning: New ranks generated below existing. Rename them in the config"))
        if self.get_max_rank() > (len(rank_list) - int(default_rank) - 3):
            current_ranks = rank_list
            for i in range(self.get_max_rank() - (
                    len(rank_list) - default_rank - 3)):
                current_ranks.insert(-2, f"Level {len(current_ranks) - 2} Constable")
            GENERIC_STATE_DATABASE.arb_state.setdefault("PolicePlugin", {})["PolicePlugin_ranks"] = current_ranks
            message.append(Label("[POLICE] Warning: New ranks generated above existing. Rename them in the config"))
        return message
