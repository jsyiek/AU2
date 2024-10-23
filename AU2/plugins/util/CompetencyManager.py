import datetime

from collections import defaultdict

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin

DEFAULT_START_COMPETENCY = 14
DEFAULT_EXTENSION = 7
ID_GAME_START = "GAME_START_COMPETENCY"
ID_DEFAULT_EXTN = "DEFAULT_EXTN"


class CompetencyManager:
    """
    Simple manager for competency
    """

    def __init__(self, game_start: datetime.datetime, auto_competency: bool = False):
        # from assassin ID to deadline
        self.deadlines = defaultdict(lambda: self.game_start + self.initial_competency_period)
        self.game_start = game_start
        self.initial_competency_period = datetime.timedelta(days=GENERIC_STATE_DATABASE.arb_int_state.get(ID_GAME_START, DEFAULT_START_COMPETENCY))
        self.activated = GENERIC_STATE_DATABASE.plugin_map.get("CompetencyPlugin", False)
        self.auto_competency = auto_competency
        self.attempts_since_kill = defaultdict(lambda: 0)

    def add_event(self, e: Event):
        for (aID, extn) in e.pluginState.get("CompetencyPlugin", {}).get("competency", {}).items():
            self.deadlines[aID] = max(
                self.deadlines[aID],
                e.datetime + datetime.timedelta(days=extn)
            )
        if self.auto_competency:
            for (killer, victim) in e.kills:
                if not ASSASSINS_DATABASE.get(victim).is_police:
                    self.attempts_since_kill[killer] = 0
                    # Allows overriding auto competency on a case-by-case basis
                    if killer not in e.pluginState.get("CompetencyPlugin", {}).get("competency", {}):
                        self.deadlines[killer] = max(
                            self.deadlines[killer],
                            e.datetime + datetime.timedelta(
                                days=e.pluginState.get("CompetencyPlugin", {})
                                    .get("current_default", GENERIC_STATE_DATABASE.arb_int_state.get(ID_DEFAULT_EXTN, DEFAULT_EXTENSION)))
                        )

            for assassin_id in e.pluginState.get("CompetencyPlugin", {}).get("attempts", []):
                # Logic for not increasing attempts if player got a player kill in same event.
                for (killer, victim) in e.kills:
                    if killer == assassin_id and not ASSASSINS_DATABASE.get(victim).is_police:
                        break
                else:
                    self.attempts_since_kill[assassin_id] += 1
                # Checks if the assassin has had 2, 4, etc attempts since last kill,
                # and the competency has not been manually overridden
                # Then grants attempt competency
                if not self.attempts_since_kill[assassin_id] % 2 and assassin_id not in e.pluginState\
                        .get("CompetencyPlugin", {}).get("competency", {}):
                    self.deadlines[assassin_id] = max(
                        self.deadlines[assassin_id],
                        e.datetime + datetime.timedelta(
                            days=e.pluginState.get("CompetencyPlugin", {})
                                .get("current_default", GENERIC_STATE_DATABASE.arb_int_state.get(ID_DEFAULT_EXTN, DEFAULT_EXTENSION)))
                    )

    def is_inco_at(self, a: Assassin, date: datetime.datetime):
        """
        Returns true if:
         1) the CompetencyPlugin is activated
         2) the assassin is not police
         3) the deadline is earlier than the date
        """
        return self.activated and not a.is_police and self.deadlines[a.identifier] < date

    def get_incos_at(self, date: datetime.datetime):
        """
        Returns all incompetents currently known that would be incompetent if no more events were added
        and the date were fastforwarded to `date`
        """
        return [a for a in ASSASSINS_DATABASE.assassins.values() if self.is_inco_at(a, date)]