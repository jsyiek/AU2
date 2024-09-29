import datetime
import os
from html import escape
from typing import List, Tuple, Dict

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.html_components.AssassinDependentCrimeEntry import AssassinDependentCrimeEntry
from AU2.html_components.Dependency import Dependency
from AU2.html_components.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.WantedManager import WantedManager

PLAYER_TABLE_TEMPLATE = """
<p xmlns="">
    This is the <b>List of Wanted players</b>.
</p>
<table xmlns="" class="playerlist">
    <tr><th>Real Name</th><th>Pseudonym</th><th>Address</th><th>College</th><th>Water Weapons Status</th><th>Crime</th><th>Redemption Conditions</th><th>Notes</th></tr>
    {ROWS}
</table>
"""


POLICE_TABLE_TEMPLATE = """
<p xmlns="">
    Those that were corrupted by the dark side of the police force....
</p>
<table xmlns="" class="playerlist">
    <tr><th>Rank</th><th>Real Name</th><th>Pseudonym</th><th>Address</th><th>College</th><th>Water Weapons Status</th><th>Crime</th><th>Redemption Conditions</th><th>Notes</th></tr>
    {ROWS}
</table>
"""

PLAYER_TABLE_ROW_TEMPLATE = "<tr><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{CRIME}</td><td>{REDEMPTION}</td><td>{NOTES}</td></tr>"
POLICE_TABLE_ROW_TEMPLATE = "<tr><td>{RANK}</td><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{CRIME}</td><td>{REDEMPTION}</td><td>{NOTES}</td></tr>"


DEAD_PLAYER_TABLE_TEMPLATE = """
<p xmlns="">
    Inevitably, this happens....
</p>
<table xmlns="" class="playerlist">
    <tr><th>Name</th><th>Pseudonym</th><th>Crime</th></tr>
    {ROWS}
</table>
"""

DEAD_PLAYER_TABLE_ROW_TEMPLATE = """<tr><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{CRIME}</td></tr>"""

NO_WANTED_PLAYERS = """<p xmlns="">Nobody has gone Wanted yet. What a bunch of law-abiding assassins.</p>"""
NO_DEAD_WANTED_PLAYERS = """<p xmlns="">No Wanted players have been killed... yet.</p>"""

WANTED_PAGE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "wanted.html"), "r") as F:
    WANTED_PAGE = F.read()


@registered_plugin
class WantedPlugin(AbstractPlugin):
    FILENAME = "wanted.html"
    WRITE_PATH = os.path.join(WEBPAGE_WRITE_LOCATION, FILENAME)

    def __init__(self):
        super().__init__("WantedPlugin")

        self.event_html_ids = {
            "Wanted": self.identifier + "_wanted"
        }

    def on_event_request_create(self) -> List[HTMLComponent]:
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentCrimeEntry(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.event_html_ids["Wanted"],
                        title="WANTED: Choose players to set a new Wanted duration",
                        default={},
                    )]
            )
        ]

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState[self.identifier] = htmlResponse[self.event_html_ids["Wanted"]]
        return [Label("[WANTED] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentCrimeEntry(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.event_html_ids["Wanted"],
                        title="WANTED: Choose players to set a new Wanted duration",
                        default=e.pluginState.get(self.identifier, {}),
                    )]
            )
        ]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState[self.identifier] = htmlResponse[self.event_html_ids["Wanted"]]
        return [Label("[WANTED] Success!")]

    """def on_page_generate(self, htmlResponse) -> List[HTMLComponent]:

        # sort by datetime to ensure we read events in chronological order
        # (umpires messing with event timings could affect the canon timeline!)
        events = sorted(list(EVENTS_DATABASE.events.values()), key=lambda event: event.datetime)

        now = datetime.datetime.now()

        wanted_manger = WantedManager()
        death_manager = DeathManager(perma_death=True)

        for e in events:
            wanted_manger.add_event(e)
            death_manager.add_event(e)

        current_wanted_players = wanted_manger.get_wanted_players(now)
        wanted_players = [player for player in current_wanted_players if not player.is_police and not death_manager.is_dead(player)]
        wanted_police = [player for player in current_wanted_players if player.is_police and not death_manager.is_dead(player)]
        '''dead_players = [(player, death_manager.get_death_timings(player)[0]) for player in ASSASSINS_DATABASE.get(death_manager.get_dead() 
                        if not player.is_police and wanted_manger.is_wanted_at(player, death_manager.get_death_timings(player)[0])]'''
        dead_police = []
        # Support for police dying multiple times
        # Intentionally has multiple copies of police if they die while corrupt multiple times
        for id in death_manager.get_dead():
            player = ASSASSINS_DATABASE.get(id)
            if player.is_police:
                for time in death_manager.death_timings[player.identifier]:
                    if wanted_manger.is_wanted_at(player)
            else:  # Assume regular player's first death is only relevant one
                pass
        '''# maps ID to datetime of expiry and (duration, crime, redemption)
        most_recent_wanted: Dict[str, Tuple[datetime.datetime, Tuple[int, str, str]]] = {}

        now = datetime.datetime.now()

        def silentpop(d: Dict[str, Tuple[int, str, str]], name: str):
            if name in d:
                del d[name]

        for e in events:  # Might be cleaner to have this in a 'WantedManager'
            for playerID in e.pluginState.get(self.identifier, {}):
                duration, crime, redemption = e.pluginState[self.identifier][playerID]
                expiry = e.datetime + datetime.timedelta(days=duration)
                most_recent_wanted[playerID] = (expiry, (duration, crime, redemption))
                if now >= expiry:
                    silentpop(wanted_players, playerID)
                    silentpop(wanted_police, playerID)
                    continue
                player = ASSASSINS_DATABASE.get(playerID)
                if player.is_police:
                    wanted_police[playerID] = (duration, crime, redemption)
                else:
                    wanted_players[playerID] = (duration, crime, redemption)

            # check to see if a victim died while wanted
            for (killer, victim) in e.kills:
                if victim in most_recent_wanted:
                    wanted_expiry, wanted_data = most_recent_wanted[victim]
                    if wanted_expiry < e.datetime:
                        continue
                    victim_assassin = ASSASSINS_DATABASE.get(victim)
                    if victim_assassin.is_police:
                        dead_police[victim] = wanted_data
                        silentpop(wanted_police, victim)
                    else:
                        dead_players[victim] = wanted_data
                        silentpop(wanted_players, victim)

        player_rows = []
        police_rows = []
        dead_player_rows = []'''

        tables = []
        if wanted_players:
            rows = []
            for playerID in wanted_players:
                player = ASSASSINS_DATABASE.get(playerID)
                (_, crime, redemption) = wanted_players[playerID]
                rows.append(
                    PLAYER_TABLE_ROW_TEMPLATE.format(
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=escape(player.all_pseudonyms()),
                        ADDRESS=escape(player.address),
                        COLLEGE=escape(player.college),
                        WATER_STATUS=escape(player.water_status),
                        CRIME=escape(crime),
                        REDEMPTION=escape(redemption),
                        NOTES=escape(player.notes)
                    )
                )
            tables.append(
                PLAYER_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )
        if wanted_police:
            for playerID in wanted_police:
                player = ASSASSINS_DATABASE.get(playerID)
                (_, crime, redemption) = wanted_police[playerID]
                police_rows.append(
                    POLICE_TABLE_ROW_TEMPLATE.format(
                        RANK="Police", # TODO: update when police rank plugin implemented
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=escape(player.all_pseudonyms()),
                        ADDRESS=escape(player.address),
                        COLLEGE=escape(player.college),
                        WATER_STATUS=escape(player.water_status),
                        CRIME=escape(crime),
                        REDEMPTION=escape(redemption),
                        NOTES=escape(player.notes)
                    )
                )

        for playerID in dead_players:
            player = ASSASSINS_DATABASE.get(playerID)
            (_, crime, _) = dead_players[playerID]
            dead_player_rows.append(
                DEAD_PLAYER_TABLE_ROW_TEMPLATE.format(
                    REAL_NAME=escape(player.real_name),
                    PSEUDONYMS=escape(player.all_pseudonyms()),
                    CRIME=escape(crime)
                )
            )

        player_table = ""
        police_table = ""
        dead_player_table = ""

        if player_rows:
            player_table = PLAYER_TABLE_TEMPLATE.format(ROWS="\n".join(player_rows))
        if police_rows:
            police_table = POLICE_TABLE_TEMPLATE.format(ROWS="\n".join(police_rows))
        if dead_player_rows:
            dead_player_table = DEAD_PLAYER_TABLE_TEMPLATE.format(ROWS="\n".join(dead_player_rows))

        wanted_html = WANTED_PAGE.format(
            PLAYER_TABLE=player_table,
            POLICE_TABLE=police_table,
            DEAD_PLAYER_TABLE=dead_player_table
        )

        with open(self.WRITE_PATH, "w+") as F:
            F.write(wanted_html)
            # TODO add year to footer

        return [Label(f"[WANTED] Saved to {self.WRITE_PATH}")]"""
