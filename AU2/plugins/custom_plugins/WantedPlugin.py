import os
from html import escape
from typing import List, Optional, Tuple

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Assassin, Event
from AU2.html_components import HTMLComponent
from AU2.html_components.DependentComponents.AssassinDependentCrimeEntry import AssassinDependentCrimeEntry
from AU2.html_components.MetaComponents.Dependency import Dependency
from AU2.html_components.SimpleComponents.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, AttributePairTableRow, ColorFnGenerator, NavbarEntry
from AU2.plugins.CorePlugin import PLUGINS, registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.custom_plugins.SRCFPlugin import Email
from AU2.plugins.util.CityWatchRankManager import CityWatchRankManager, AUTO_RANK_DEFAULT, CITY_WATCH_KILLS_RANKUP_DEFAULT, \
    DEFAULT_RANKS, DEFAULT_CITY_WATCH_RANK
from AU2.plugins.util.WantedManager import WantedManager
from AU2.plugins.util.colors import CORRUPT_CITY_WATCH_COLS, WANTED_COLS
from AU2.plugins.util.date_utils import get_now_dt

PLAYER_TABLE_TEMPLATE = """
<p xmlns="">
    This is the <b>List of Wanted players</b>.
</p>
<table xmlns="" class="playerlist">
    <tr><th>Real Name</th><th>Pseudonym</th><th>Address</th><th>College</th><th>Room Water Weapons Status</th><th>Crime</th><th>Redemption Conditions</th><th>Notes</th></tr>
    {ROWS}
</table>
"""

CITY_WATCH_TABLE_TEMPLATE = """
<p xmlns="">
    Those that were corrupted by the dark side of the city watch....
</p>
<table xmlns="" class="playerlist">
    <tr><th>Rank</th><th>Real Name</th><th>Pseudonym</th><th>Address</th><th>College</th><th>Room Water Weapons Status</th><th>Crime</th><th>Redemption Conditions</th><th>Notes</th></tr>
    {ROWS}
</table>
"""

DEAD_WANTED_INTRO_TEXT = """
<p xmlns="">
    Here are the names of those that paid the price for their crimes...
</p>
"""

DEAD_PLAYER_TABLE_TEMPLATE = """
<table xmlns="" class="playerlist">
    <tr><th>Name</th><th>Pseudonym</th><th>Crime</th></tr>
    {ROWS}
</table>
<p></p>
"""

DEAD_CORRUPT_CITY_WATCH_TABLE_TEMPLATE = """
<table xmlns="" class="playerlist">
  <tr><th>Rank</th><th>Name</th><th>Pseudonym</th><th>Crime</th></tr>
  {ROWS}
</table>
"""
PLAYER_TABLE_ROW_TEMPLATE = "<tr><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{CRIME}</td><td>{REDEMPTION}</td><td>{NOTES}</td></tr>"
CITY_WATCH_TABLE_ROW_TEMPLATE = "<tr><td>{RANK}</td><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{CRIME}</td><td>{REDEMPTION}</td><td>{NOTES}</td></tr>"
DEAD_PLAYER_TABLE_ROW_TEMPLATE = """<tr><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{CRIME}</td></tr>"""
DEAD_CORRUPT_CITY_WATCH_TABLE_ROW_TEMPLATE = """<tr><td>{RANK}</td><td>{REAL_NAME}</td><td>{PSEUDONYMS}</td><td>{CRIME}</td></tr>"""

NO_WANTED_PLAYERS = """<p xmlns="">Nobody is Wanted at the moment. What a bunch of law-abiding assassins.</p>"""
NO_DEAD_WANTED_PLAYERS = """<p xmlns="">No Wanted players have been killed... yet.</p>"""

WANTED_NAVBAR_ENTRY = NavbarEntry("wanted.html", "Wanted list", 1)

WANTED_PAGE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "wanted.html"), "r", encoding="utf-8", errors="ignore") as F:
    WANTED_PAGE = F.read()


@registered_plugin
class WantedPlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("WantedPlugin")

        self.event_html_ids = {
            "Wanted": self.identifier + "_wanted"
        }

    def colour_fn_generator(self) -> ColorFnGenerator:
        wanted_manager = WantedManager()
        yield_next = None
        while True:
            e = yield yield_next
            wanted_manager.add_event(e)

            def color_fn(assassin: Assassin, pseudonym: str) -> Optional[Tuple[float, str]]:
                """Special colouring for wanted players"""
                if wanted_manager.is_player_wanted(assassin.identifier, time=e.datetime):
                    ind = sum(ord(c) for c in pseudonym)
                    if assassin.is_police:
                        return 6, CORRUPT_CITY_WATCH_COLS[ind % len(CORRUPT_CITY_WATCH_COLS)]
                    else:
                        return 6, WANTED_COLS[ind % len(WANTED_COLS)]

            yield_next = color_fn

        Assassin.__last_emailed_crime = self.assassin_property("last_emailed_crime", None, store_default=False)

    def on_event_request_create(self) -> List[HTMLComponent]:
        data = {}
        PLUGINS.data_hook("WantedPlugin_targeting_graph", data)
        targeting_graph = data.get("targeting_graph", {})
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    Dependency(
                        dependentOn="CorePlugin_kills",
                        htmlComponents=[
                            AssassinDependentCrimeEntry(
                                pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                                identifier=self.event_html_ids["Wanted"],
                                title="WANTED: Choose players to set a new Wanted duration",
                                default={},
                                kill_entry_identifier="CorePlugin_kills",
                                targeting_graph=targeting_graph
                            )
                        ]
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
                    Dependency(
                        dependentOn="CorePlugin_kills",
                        htmlComponents=[
                            AssassinDependentCrimeEntry(
                                pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                                identifier=self.event_html_ids["Wanted"],
                                title="WANTED: Choose players to set a new Wanted duration",
                                default=e.pluginState.get(self.identifier, {}),
                                kill_entry_identifier="CorePlugin_kills",
                                targeting_graph={}
                            )
                        ]
                    )]
            )
        ]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState[self.identifier] = htmlResponse[self.event_html_ids["Wanted"]]
        return [Label("[WANTED] Success!")]

    def render_event_summary(self, event: Event) -> List[AttributePairTableRow]:
        results = []
        for playerID in event.pluginState.get(self.identifier, ()):
            a = ASSASSINS_DATABASE.get(playerID)
            sec_id = a._secret_id
            name = a.real_name.split(" ")
            if len(name) > 0:
                name = name[0]
            else:
                name = "<no name...?!>"
            duration, crime, redemption = event.pluginState[self.identifier][playerID]
            results.append((f"Wanted duration ({name} {sec_id})", str(duration) + " days"))
            results.append((f"Wanted crime ({name} {sec_id})", crime))
            results.append((f"Wanted redemption ({name} {sec_id})", redemption))
        return results

    def on_page_generate(self, htmlResponse, navbar_entries) -> List[HTMLComponent]:
        messages = []
        # sort by datetime to ensure we read events in chronological order
        # (umpires messing with event timings could affect the canon timeline!)
        events = sorted(list(EVENTS_DATABASE.events.values()), key=lambda event: event.datetime)

        city_watch_ranks_enabled = GENERIC_STATE_DATABASE.plugin_map.get("CityWatchPlugin", False)

        wanted_manager = WantedManager()
        if city_watch_ranks_enabled:
            city_watch_rank_manager = CityWatchRankManager(
                auto_ranking=GENERIC_STATE_DATABASE.arb_state.get("CityWatchPlugin", {}).get(
                    "CityWatchPlugin_auto_rank", AUTO_RANK_DEFAULT),
                city_watch_kill_ranking=GENERIC_STATE_DATABASE.arb_state.get("CityWatchPlugin", {}).get(
                    "CityWatchPlugin_city_watch_kills_rankup", CITY_WATCH_KILLS_RANKUP_DEFAULT)
            )
            for e in events:
                city_watch_rank_manager.add_event(e)
            messages += city_watch_rank_manager.generate_new_ranks_if_necessary()

        for e in events:
            wanted_manager.add_event(e)

        wanted_players = wanted_manager.get_live_wanted_players(city_watch=False)
        wanted_city_watch = wanted_manager.get_live_wanted_players(city_watch=True)
        wanted_player_deaths = wanted_manager.get_wanted_player_deaths(city_watch=False)
        wanted_city_watch_deaths = wanted_manager.get_wanted_player_deaths(city_watch=True)

        tables = []
        if wanted_players:
            rows = []
            for player_id in wanted_players:
                player = ASSASSINS_DATABASE.get(player_id)
                rows.append(
                    PLAYER_TABLE_ROW_TEMPLATE.format(
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=player.all_pseudonyms(),
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
        if wanted_city_watch:
            rows = []
            # TODO: These look like they can be deleted? Pycharm identifies default_rank and ranks as unread vars
            if city_watch_ranks_enabled:
                default_rank = GENERIC_STATE_DATABASE.arb_state.get(
                    "CityWatchPlugin", {}).get("CityWatchPlugin_default_rank", DEFAULT_CITY_WATCH_RANK)
                ranks = GENERIC_STATE_DATABASE.arb_state.get("CityWatchPlugin", {}).get("CityWatchPlugin_ranks", DEFAULT_RANKS)
            for player_id in wanted_city_watch:
                player = ASSASSINS_DATABASE.get(player_id)
                rank = "City Watch"
                if city_watch_ranks_enabled:
                    rank = city_watch_rank_manager.get_rank_name(player_id)
                rows.append(
                    CITY_WATCH_TABLE_ROW_TEMPLATE.format(
                        RANK=rank,
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=player.all_pseudonyms(),
                        ADDRESS=escape(player.address),
                        COLLEGE=escape(player.college),
                        WATER_STATUS=escape(player.water_status),
                        CRIME=escape(wanted_city_watch[player_id]['crime']),
                        REDEMPTION=escape(wanted_city_watch[player_id]['redemption']),
                        NOTES=escape(player.notes)
                    )
                )
            tables.append(
                CITY_WATCH_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )
        if wanted_player_deaths or wanted_player_deaths:
            tables.append(DEAD_WANTED_INTRO_TEXT)
        if wanted_player_deaths:
            rows = []
            for wanted_death_event in wanted_player_deaths:
                player = ASSASSINS_DATABASE.get(wanted_death_event['player_id'])
                rows.append(
                    DEAD_PLAYER_TABLE_ROW_TEMPLATE.format(
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=player.all_pseudonyms(),
                        CRIME=escape(wanted_death_event['crime'])
                    )
                )
            tables.append(
                DEAD_PLAYER_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )
        if wanted_city_watch_deaths:
            rows = []
            for wanted_death_event in wanted_city_watch_deaths:
                player = ASSASSINS_DATABASE.get(wanted_death_event['player_id'])
                rank = "City Watch"
                if city_watch_ranks_enabled:
                    rank = city_watch_rank_manager.get_rank_name(wanted_death_event['player_id'])
                rows.append(
                    DEAD_CORRUPT_CITY_WATCH_TABLE_ROW_TEMPLATE.format(
                        RANK=rank,
                        REAL_NAME=escape(player.real_name),
                        PSEUDONYMS=player.all_pseudonyms(),
                        CRIME=escape(wanted_death_event['crime'])
                    )
                )
            tables.append(
                DEAD_CORRUPT_CITY_WATCH_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )

        if not tables:
            tables.append(NO_WANTED_PLAYERS)
        else:
            navbar_entries.append(WANTED_NAVBAR_ENTRY)
            if not (wanted_city_watch_deaths or wanted_player_deaths):
                tables.append(NO_DEAD_WANTED_PLAYERS)

        with open(WEBPAGE_WRITE_LOCATION / WANTED_NAVBAR_ENTRY.url, "w+", encoding="utf-8", errors="ignore") as F:
            F.write(
                WANTED_PAGE.format(
                    CONTENT="\n".join(tables),
                    YEAR=get_now_dt().year
                )
            )
        messages.append(Label("[WANTED] Success!"))
        return messages

    def on_hook_respond(self, hook: str, html_response, data) -> List[HTMLComponent]:
        if hook == "SRCFPlugin_email":
            events = list(EVENTS_DATABASE.events.values())
            events.sort(key=lambda event: event.datetime)

            wanted_manager = WantedManager()
            for e in events:
                wanted_manager.add_event(e)

            wanted_data = wanted_manager.get_live_wanted_players(city_watch=False)
            corrupt_data = wanted_manager.get_live_wanted_players(city_watch=True)

            email_list: List[Email] = data
            for email in email_list:
                recipient = email.recipient.identifier
                crime_data = wanted_data.get(recipient, corrupt_data.get(recipient))
                last_emailed_crime = email.recipient.__last_emailed_crime
                content = ""
                require_send = False
                if crime_data:
                    content = (f"You are currently {'WANTED' if recipient in wanted_data else 'CORRUPT'}.\n" 
                               f"Reason: {crime_data['crime']}\n"
                               f"Redemption conditions: {crime_data['redemption']}")
                    require_send = crime_data != last_emailed_crime
                elif last_emailed_crime:
                    content = ("You have been REDEEMED and are no longer on the "
                              f"{'corrupt' if email.recipient.is_city_watch else 'wanted'} list.")
                    require_send = crime_data != last_emailed_crime

                if content:
                    email.add_content(
                        self.identifier,
                        content=content,
                        require_send=require_send,
                    )
                    # the component is named confusingly. here, True = *do* send emails!
                    if html_response.get("SRCFPlugin_dry_run", True):
                        email.recipient.__last_emailed_crime = crime_data
        return []
