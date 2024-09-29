import datetime

from typing import Dict, Tuple, List

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin


class WantedManager:
    """
    Simple manager for wantedness
    """

    def __init__(self):
        self.activated = GENERIC_STATE_DATABASE.plugin_map.get("WantedPlugin", False)
        self.wanted_events: Dict[str, List[Tuple[datetime.datetime, Tuple[int, str, str]]]] = {}

    def add_event(self, e: Event):
        for playerID in e.pluginState.get("WantedPlugin", {}):
            duration, crime, redemption = e.pluginState["WantedPlugin"][playerID]
            expiry = e.datetime + datetime.timedelta(days=duration)
            self.wanted_events.setdefault(playerID, [])
            self.wanted_events[playerID].append((expiry, (duration, crime, redemption)))

    def is_wanted_at(self, a: Assassin, date: datetime.datetime):
        """
        Returns true if:
         1) the WantedPlugin is activated
         2) `a` has a wanted event before `date`
         2) `a`'s most recent wanted_event (at `date`) puts them wanted at `date`
        """
        if self.activated:
            if not self.wanted_events[a.identifier]:
                return False
            most_recent_event = 0
            for i in self.wanted_events[a.identifier]:
                if (i[0] - datetime.timedelta(days=i[1][0])) > date:
                    break
                most_recent_event = i
            if not most_recent_event:
                return False
            else:
                return most_recent_event[0] > date
        else:
            return False

    def get_wanted_players(self, date: datetime.datetime):
        """
        Returns all players who are wanted at `date`
        """
        return [a for a in ASSASSINS_DATABASE.assassins.values() if self.is_wanted_at(a, date)]

    def get_wanted_player_crime_info(self, a: Assassin, date: datetime.datetime):
        """
        Returns `a`'s most recent wanted event at `date`
        Returns False if they aren't wanted
        Ideally only used if `a` is known to be wanted at `date`
        Almost certainly a better way to do this, but I can't think
        """
        if self.is_wanted_at(a, date):
            for i in self.wanted_events[a.identifier]:
                if (i[0] - datetime.timedelta(days=i[1][0])) > date:
                    break
                most_recent_event = i
            return most_recent_event
        return False
