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
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION

PLAYER_TABLE_TEMPLATE = """<table xmlns="" class="playerlist">
<tr><th>Real Name</th><th>Pseudonym</th><th>Address</th><th>College</th><th>Water Weapons Status</th><th>Crime</th><th>Redemption Conditions</th><th>Notes</th></tr>
{ROWS}
</table>"""

POLICE_TABLE_TEMPLATE = """<table xmlns="" class="playerlist">
<tr><th>Rank</th><th>Real Name</th><th>Pseudonym</th><th>Address</th><th>College</th><th>Water Weapons Status</th><th>Crime</th><th>Redemption Conditions</th><th>Notes</th></tr>
{ROWS}
</table>"""

PLAYER_TABLE_ROW_TEMPLATE = "<tr><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{CRIME}</td><td>{REDEMPTION}</td><td>{NOTES}</td></tr>"
POLICE_TABLE_ROW_TEMPLATE = "<tr><td>{RANK}</td><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{CRIME}</td><td>{REDEMPTION}</td><td>{NOTES}</td></tr>"


DEAD_PLAYER_TABLE_TEMPLATE = """<table xmlns="" class="playerlist">
<tr><th>Name</th><th>Pseudonym</th><th>Crime</th></tr>
{ROWS}
</table>"""

DEAD_PLAYER_TABLE_ROW_TEMPLATE = """<tr><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{CRIME}</td></tr>"""

WANTED_PAGE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "wanted.html"), "r") as F:
    WANTED_PAGE = F.read()


class WantedPlugin(AbstractPlugin):
    FILENAME = "wanted.html"
    WRITE_PATH = os.path.join(WEBPAGE_WRITE_LOCATION, FILENAME)

    def __init__(self):
        super().__init__("WantedPlugin")

        self.event_html_ids = {
            "Wanted": self.identifier + "_wanted"
        }

        self.exports = [
            Export(
                "generate_page_wanted",
                "Generate page -> Wanted",
                self.ask_generate_page,
                self.answer_generate_page
            ),
        ]

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

    def ask_generate_page(self) -> List[HTMLComponent]:
        return [Label("[WANTED] Preparing...")]

    def answer_generate_page(self, _) -> List[HTMLComponent]:

        # sort by datetime to ensure we read events in chronological order
        # (umpires messing with event timings could affect the canon timeline!)
        events = sorted(list(EVENTS_DATABASE.events.values()), key=lambda event: event.datetime)

        wanted_players = {}
        wanted_police = {}
        dead_players = {}
        dead_police = {} # currently unused - keeping it calculated incase we want to display dead wanted police

        # maps ID to datetime of expiry and (duration, crime, redemption)
        most_recent_wanted: Dict[str, Tuple[datetime.datetime, Tuple[int, str, str]]] = {}

        now = datetime.datetime.now()

        def silentpop(d: Dict[str, Tuple[int, str, str]], name: str):
            if name in d:
                del d[name]

        for e in events:
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

        """
        
    PLAYER_TABLE_ROW_TEMPLATE = 
    "<tr><td>{REAL NAME}</td><td>{PSEUDONYMS}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{CRIME}</td><td>{REDEMPTION}</td><td>{NOTES}</td></tr>"
    POLICE_TABLE_ROW_TEMPLATE = 
    "<tr><td>{RANK}</td><td>{REAL NAME}</td><td>{PSEUDONYMS}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{CRIME}</td><td>{REDEMPTION}</td><td>{NOTES}</td></tr>"
        """
        player_rows = []
        police_rows = []
        dead_player_rows = []
        for playerID in wanted_players:
            player = ASSASSINS_DATABASE.get(playerID)
            (_, crime, redemption) = wanted_players[playerID]
            player_rows.append(
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

        return [Label(f"[WANTED] Saved to {self.WRITE_PATH}")]
