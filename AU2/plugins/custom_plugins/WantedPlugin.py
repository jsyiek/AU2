import datetime
import os
from html import escape
from typing import List

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.html_components.AssassinDependentCrimeEntry import AssassinDependentCrimeEntry
from AU2.html_components.Dependency import Dependency
from AU2.html_components.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin
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

DEAD_PLAYER_TABLE_TEMPLATE = """
<p xmlns="">
    Inevitably, this happens....
</p>
<table xmlns="" class="playerlist">
    <tr><th>Name</th><th>Pseudonym</th><th>Crime</th></tr>
    {ROWS}
</table>
"""

DEAD_CORRUPT_POLICE_TABLE_TEMPLATE = """
<p xmlns="">
    And these are the names of those who turned to the dark side, and paid the price:
</p>
<table xmlns="" class="playerlist">
  <tr><th>Rank</th><th>Name</th><th>Pseudonym</th><th>Crime</th></tr>
  {ROWS}
</table>
"""
PLAYER_TABLE_ROW_TEMPLATE = "<tr><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{CRIME}</td><td>{REDEMPTION}</td><td>{NOTES}</td></tr>"
POLICE_TABLE_ROW_TEMPLATE = "<tr><td>{RANK}</td><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{CRIME}</td><td>{REDEMPTION}</td><td>{NOTES}</td></tr>"
DEAD_PLAYER_TABLE_ROW_TEMPLATE = """<tr><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{CRIME}</td></tr>"""
DEAD_CORRUPT_POLICE_TABLE_ROW_TEMPLATE = """<tr><td>{RANK}</td><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{CRIME}</td></tr>"""

NO_WANTED_PLAYERS = """<p xmlns="">Nobody has gone Wanted yet. What a bunch of law-abiding assassins.</p>"""
NO_DEAD_WANTED_PLAYERS = """<p xmlns="">No Wanted players have been killed... yet.</p>"""

WANTED_PAGE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "wanted.html"), "r") as F:
    WANTED_PAGE = F.read()


@registered_plugin
class WantedPlugin(AbstractPlugin):
    FILENAME = "wanted.html"

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

    def on_page_generate(self, htmlResponse) -> List[HTMLComponent]:

        # sort by datetime to ensure we read events in chronological order
        # (umpires messing with event timings could affect the canon timeline!)
        events = sorted(list(EVENTS_DATABASE.events.values()), key=lambda event: event.datetime)

        now = datetime.datetime.now()

        wanted_manager = WantedManager()
        death_manager = DeathManager(perma_death=True)

        for e in events:
            wanted_manager.add_event(e)
            death_manager.add_event(e)

        current_wanted_players = wanted_manager.get_wanted_players(now)
        wanted_players = [player for player in current_wanted_players if not player.is_police and not death_manager.is_dead(player)]
        wanted_police = [player for player in current_wanted_players if player.is_police and not death_manager.is_dead(player)]
        # TODO Put dead police on the corrupt list if they have been made re-corrupt after dying, I think
        dead_players_times = []
        dead_police_times = []
        # Support for police dying multiple times
        # Intentionally has multiple copies of police if they die while corrupt multiple times
        for player_id in set(death_manager.get_dead()):
            player = ASSASSINS_DATABASE.get(player_id)
            if player.is_police:
                for time in death_manager.death_timings[player_id]:
                    if wanted_manager.is_wanted_at(player, time):
                        dead_police_times.append((player, time))
            else:  # Assume regular player's first death is only relevant one
                if wanted_manager.is_wanted_at(player, death_manager.death_timings[player_id][0]):
                    dead_players_times.append((player, death_manager.death_timings[player_id][0]))

        tables = []
        if wanted_players:
            rows = []
            for player in wanted_players:
                (_, crime, redemption) = wanted_manager.get_wanted_player_crime_info(player, now)[1]
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
            rows = []
            for player in wanted_police:
                (_, crime, redemption) = wanted_manager.get_wanted_player_crime_info(player, now)[1]
                rows.append(
                    POLICE_TABLE_ROW_TEMPLATE.format(
                        RANK="Police",
                        # TODO: update when police rank plugin refactored such that it is possible to get the rank name,
                        # Rank names can be generated when generate_pages is run, and this might run first, breaking it
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
                POLICE_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )
        if dead_players_times:
            rows = []
            for player, time in dead_players_times:
                (_, crime, _) = wanted_manager.get_wanted_player_crime_info(player, time)[1]
                rows.append(
                    DEAD_PLAYER_TABLE_ROW_TEMPLATE.format(
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=escape(player.all_pseudonyms()),
                        CRIME=escape(crime)
                    )
                )
            tables.append(
                DEAD_PLAYER_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )
        if dead_police_times:  # TODO Make this generate on the police page, as before
            rows = []
            for player, time in dead_police_times:
                (_, crime, _) = wanted_manager.get_wanted_player_crime_info(player, time)[1]
                rows.append(
                    DEAD_CORRUPT_POLICE_TABLE_ROW_TEMPLATE.format(
                        RANK="Police",  # TODO Same as above; make ranks work
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=escape(player.all_pseudonyms()),
                        CRIME=escape(crime)
                    )
                )
            tables.append(
                DEAD_CORRUPT_POLICE_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )

        if not tables:
            tables.append(NO_WANTED_PLAYERS)
        elif not (dead_police_times or dead_players_times):
            tables.append(NO_DEAD_WANTED_PLAYERS)

        with open(os.path.join(WEBPAGE_WRITE_LOCATION, self.FILENAME), "w+") as F:
            F.write(
                WANTED_PAGE.format(
                    CONTENT="\n".join(tables),
                    YEAR=datetime.datetime.now().year
                )
            )

        return [Label("[WANTED] Success!")]
