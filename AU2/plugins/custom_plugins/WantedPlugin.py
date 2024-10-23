import datetime
import os
from html import escape
from typing import List

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.html_components.AssassinDependentCrimeEntry import AssassinDependentCrimeEntry
from AU2.html_components.Dependency import Dependency
from AU2.html_components.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.PoliceRankManager import PoliceRankManager, AUTO_RANK_DEFAULT, POLICE_KILLS_RANKUP_DEFAULT, \
    DEFAULT_RANKS, DEFAULT_POLICE_RANK
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
        messages = []
        # sort by datetime to ensure we read events in chronological order
        # (umpires messing with event timings could affect the canon timeline!)
        events = sorted(list(EVENTS_DATABASE.events.values()), key=lambda event: event.datetime)

        now = datetime.datetime.now()

        police_ranks_enabled = GENERIC_STATE_DATABASE.plugin_map.get("PolicePlugin", False)

        wanted_manager = WantedManager(current_time=now)
        if police_ranks_enabled:
            police_rank_manager = PoliceRankManager(
                auto_ranking=GENERIC_STATE_DATABASE.arb_state.get("PolicePlugin", {}).get(
                    "PolicePlugin_auto_rank", AUTO_RANK_DEFAULT),
                police_kill_ranking=GENERIC_STATE_DATABASE.arb_state.get("PolicePlugin", {}).get(
                    "PolicePlugin_police_kills_rankup", POLICE_KILLS_RANKUP_DEFAULT)
            )
            for e in events:
                police_rank_manager.add_event(e)

        for e in events:
            wanted_manager.add_event(e)

        wanted_players = wanted_manager.get_live_wanted_players(police=False)
        wanted_police = wanted_manager.get_live_wanted_players(police=True)
        wanted_player_deaths = wanted_manager.get_wanted_player_deaths(police=False)
        wanted_police_deaths = wanted_manager.get_wanted_player_deaths(police=True)

        tables = []
        if wanted_players:
            rows = []
            for player_id in wanted_players:
                player = ASSASSINS_DATABASE.get(player_id)
                rows.append(
                    PLAYER_TABLE_ROW_TEMPLATE.format(
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=escape(player.all_pseudonyms()),
                        ADDRESS=escape(player.address),
                        COLLEGE=escape(player.college),
                        WATER_STATUS=escape(player.water_status),
                        CRIME=escape(wanted_players[player_id]['crime']),
                        REDEMPTION=escape(wanted_players[player_id]['redemption']),
                        NOTES=escape(player.notes)
                    )
                )
            tables.append(
                PLAYER_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )
        if wanted_police:
            rows = []
            if police_ranks_enabled:
                default_rank = GENERIC_STATE_DATABASE.arb_state.get(
                    "PolicePlugin", {}).get("PolicePlugin_default_rank", DEFAULT_POLICE_RANK)
                ranks = GENERIC_STATE_DATABASE.arb_state.get("PolicePlugin", {}).get("PolicePlugin_ranks", DEFAULT_RANKS)
            for player_id in wanted_police:
                player = ASSASSINS_DATABASE.get(player_id)
                rank = "Police"
                if police_ranks_enabled:
                    rank_no = police_rank_manager.get_relative_rank(player) + default_rank
                    try:
                        rank = ranks[rank_no]
                    except IndexError:
                        # Lets the user know if the ranks break due to PolicePlugin.generate_pages not generating new ranks in time.
                        # Could maybe be avoided with a refactor of how ranks work, but I really don't want to do that now
                        # TODO Refactor policerankmanager to also manage rank names, not just relative numbers
                        rank = '[ERROR]'
                        messages.append(Label("[WANTED] WARNING: Error in police ranks. Generate pages again to fix"))
                rows.append(
                    POLICE_TABLE_ROW_TEMPLATE.format(
                        RANK=rank,
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=escape(player.all_pseudonyms()),
                        ADDRESS=escape(player.address),
                        COLLEGE=escape(player.college),
                        WATER_STATUS=escape(player.water_status),
                        CRIME=escape(wanted_police[player_id]['crime']),
                        REDEMPTION=escape(wanted_police[player_id]['redemption']),
                        NOTES=escape(player.notes)
                    )
                )
            tables.append(
                POLICE_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )
        if wanted_player_deaths:
            rows = []
            for wanted_death_event in wanted_player_deaths:
                player = ASSASSINS_DATABASE.get(wanted_death_event['player_id'])
                rows.append(
                    DEAD_PLAYER_TABLE_ROW_TEMPLATE.format(
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=escape(player.all_pseudonyms()),
                        CRIME=escape(wanted_death_event['crime'])
                    )
                )
            tables.append(
                DEAD_PLAYER_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )
        if wanted_police_deaths:
            rows = []
            if police_ranks_enabled:
                default_rank = GENERIC_STATE_DATABASE.arb_state.get(
                    "PolicePlugin", {}).get("PolicePlugin_default_rank", DEFAULT_POLICE_RANK)
                ranks = GENERIC_STATE_DATABASE.arb_state.get("PolicePlugin", {}).get("PolicePlugin_ranks", DEFAULT_RANKS)
            for wanted_death_event in wanted_police_deaths:
                player = ASSASSINS_DATABASE.get(wanted_death_event['player_id'])
                rank = "Police"
                if police_ranks_enabled:
                    rank_no = police_rank_manager.get_relative_rank(player) + default_rank
                    try:
                        rank = ranks[rank_no]
                    except IndexError:
                        rank = '[ERROR]'
                        messages.append(Label("[WANTED] WARNING: Error in police ranks. Generate pages again to fix"))
                rows.append(
                    DEAD_CORRUPT_POLICE_TABLE_ROW_TEMPLATE.format(
                        RANK=rank,
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=escape(player.all_pseudonyms()),
                        CRIME=escape(wanted_death_event['crime'])
                    )
                )
            tables.append(
                DEAD_CORRUPT_POLICE_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )

        if not tables:
            tables.append(NO_WANTED_PLAYERS)
        elif not (wanted_police_deaths or wanted_player_deaths):
            tables.append(NO_DEAD_WANTED_PLAYERS)

        with open(os.path.join(WEBPAGE_WRITE_LOCATION, self.FILENAME), "w+") as F:
            F.write(
                WANTED_PAGE.format(
                    CONTENT="\n".join(tables),
                    YEAR=datetime.datetime.now().year
                )
            )
        messages.append(Label("[WANTED] Success!"))
        return messages
