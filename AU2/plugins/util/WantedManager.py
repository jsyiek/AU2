import datetime
from typing import Dict, List

from AU2 import TIMEZONE
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event
from AU2.plugins.util.date_utils import get_now_dt


class WantedManager:
    """
    (Not so) Simple manager for wantedness
    """

    def __init__(self):
        self.activated = GENERIC_STATE_DATABASE.plugin_map.get("WantedPlugin", False)
        # Relevent events are dicts, either {event_time: datetime.datetime, wanted_duration: days, crime: str, redemption: str},
        # or {event_time}, which represents a death at event_time. This allows for multiple deaths (for police or may week)
        self.wanted_events: Dict[str, List[Dict]] = {}

    def add_event(self, e: Event):
        for playerID in e.pluginState.get("WantedPlugin", {}):
            duration, crime, redemption = e.pluginState["WantedPlugin"][playerID]
            self.wanted_events.setdefault(playerID, [])
            self.wanted_events[playerID].append({'event_time': e.datetime,
                                                 'wanted_duration': datetime.timedelta(days=duration),
                                                 'crime': crime,
                                                 'redemption': redemption})
        for (killer, victim) in e.kills:
            self.wanted_events.setdefault(victim, [])
            self.wanted_events[victim].append({'event_time': e.datetime})

    def get_live_wanted_players(self, police=False):
        players = {}
        for player_id in self.wanted_events:
            if ASSASSINS_DATABASE.get(player_id).is_police != police:
                continue
            if self.is_player_wanted(player_id):
                last_event = self.wanted_events[player_id][-1]
                players[player_id] = {'crime': last_event['crime'], 'redemption': last_event['redemption']}
        return players

    def is_player_wanted(self, player_id, time=get_now_dt()):
        if not self.activated:
            return False
        if player_id not in self.wanted_events:
            return False
        last_event = self.wanted_events[player_id][-1]
        if len(last_event) == 1:
            # if a players last event is a death, then they haven't committed a post-resurrection crime, so ignore
            return False
        # Check most recent event for wanted info. No support for multiple active wanted_events per player
        if last_event['event_time'] + last_event['wanted_duration'] > time:
            return True

    def get_wanted_player_deaths(self, police=False):
        wanted_deaths = []
        for player_id in self.wanted_events:
            if ASSASSINS_DATABASE.get(player_id).is_police != police:
                continue
            for idx, wanted_event in enumerate(self.wanted_events[player_id]):
                # ignore if not a death event, or it's a death before any wanted events
                if len(wanted_event.keys()) != 1 or idx == 0:
                    continue
                preceding_event = self.wanted_events[player_id][idx-1]
                # ignore if second death in a row
                if len(preceding_event.keys()) == 1:
                    continue
                if preceding_event['event_time'] + preceding_event['wanted_duration'] >= wanted_event['event_time']:
                    wanted_deaths.append({
                        'player_id': player_id,
                        'crime': preceding_event['crime'],
                        'death_time': wanted_event['event_time']
                    })
        return sorted(wanted_deaths, key=lambda x: x['death_time'])

