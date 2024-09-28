import datetime
import os
from typing import List

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Assassin, Event
from AU2.html_components import HTMLComponent
from AU2.html_components.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.Dependency import Dependency
from AU2.html_components.Label import Label
from AU2.html_components.LargeTextEntry import LargeTextEntry
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.PoliceRankManager import DEFAULT_RANKS, PoliceRankManager, DEFAULT_POLICE_RANK, AUTO_RANK_DEFAULT, \
    MANUAL_RANK_DEFAULT, POLICE_KILLS_RANKUP_DEFAULT

POLICE_TABLE_TEMPLATE = """
<p xmlns="">
    Here is a list of members of our loyal police, charged with protecting Cambridge from murderers of innocents and people that annoy the all powerful Umpire:
</p>
<table xmlns="" class="playerlist">
  <tr><th>Rank</th><th>Pseudonym</th><th>Real Name</th><th>Email Address</th><th>College</th><th>Notes</th></tr>
  {ROWS}
</table>
"""

POLICE_TABLE_ROW_TEMPLATE = """
<tr><td>{RANK}</td><td>{PSEUDONYM}</td><td>{NAME}</td><td>{EMAIL}</td><td>{COLLEGE}</td><td>{NOTES}</td></tr>
"""

DEAD_POLICE_TABLE_TEMPLATE = """
<p xmlns="">
    Killed in the line of duty:
</p>
<table xmlns="" class="playerlist">
  <tr><th>Rank</th><th>Pseudonym</th><th>Real Name</th><th>Email Address</th><th>College</th><th>Notes</th></tr>
  {ROWS}
</table>
"""

DEAD_POLICE_TABLE_ROW_TEMPLATE = """
<tr><td>{RANK}</td><td>{PSEUDONYM}</td><td>{NAME}</td><td>{EMAIL}</td><td>{COLLEGE}</td><td>{NOTES}</td></tr>
"""

DEAD_CORRUPT_POLICE_TABLE_TEMPLATE = """
<p xmlns="">
    And these are the names of those who turned to the dark side, and paid the price:
</p>
<table xmlns="" class="playerlist">
  <tr><th>Rank</th><th>Pseudonym</th><th>Real Name</th><th>Email Address</th><th>College</th><th>Notes</th></tr>
  {ROWS}
</table>
"""

DEAD_CORRUPT_POLICE_TABLE_ROW_TEMPLATE = """
<tr><td>{RANK}</td><td>{PSEUDONYM}</td><td>{NAME}</td><td>{EMAIL}</td><td>{COLLEGE}</td><td>{NOTES}</td></tr>
"""

NO_DEAD_POLICE = """<p xmlns="">No police have been killed... yet.</p>"""
NO_POLICE = """<p xmlns="">The police force is suspiciously understaffed at the moment</p>"""


POLICE_PAGE_TEMPLATE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "police.html"), "r") as F:
    POLICE_PAGE_TEMPLATE = F.read()

@registered_plugin
class PolicePlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("PolicePlugin")

        self.html_ids = {
            "Ranks": self.identifier + "_ranks",
            "Relative Rank": self.identifier + "_rank_relative",
        }

        self.plugin_state = {
            "Ranks": {'id': self.identifier + "_ranks", 'default': DEFAULT_RANKS},  # List
            "Default Rank": {'id': self.identifier + "_default_rank", 'default': DEFAULT_POLICE_RANK},  # Int
            "Auto Rank": {'id': self.identifier + "_auto_rank", 'default': AUTO_RANK_DEFAULT},  # Bool
            "Manual Rank": {'id': self.identifier + "_manual_rank", 'default': MANUAL_RANK_DEFAULT},  # Bool
            "Police Kills Rankup": {'id': self.identifier + "police_kills_rankup", 'default': POLICE_KILLS_RANKUP_DEFAULT}  # Bool
        }

        self.config_exports = [
            ConfigExport(
                "PolicePlugin_set_ranks",
                "Police -> Set Ranks",
                self.ask_set_ranks,
                self.answer_set_ranks
            ),
            ConfigExport(
                "PolicePlugin_toggle_auto",
                "Police -> Toggle Auto Ranking",
                lambda *args: [],
                self.answer_toggle_auto
            ),
            ConfigExport(
                "PolicePlugin_toggle_manual",
                "Police -> Toggle Manual Ranking",
                lambda *args: [],
                self.answer_toggle_manual
            ),
            ConfigExport(
                "PolicePlugin_toggle_police_kills_rankup",
                "Police -> Toggle Ranking up on Police Kills",
                lambda *args: [],
                self.answer_toggle_police_kills_rankup
            )
        ]

    # I've done the database stuff in such a way that configs are only stored if changed; otherwise the hardcoded default configs are used.
    # Not sure how sensible this is, but it seems to work

    def gsdb_get(self, plugin_state_id):
        return GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get(self.plugin_state[plugin_state_id]['id'], self.plugin_state[plugin_state_id]['default'])

    def gsdb_set(self, plugin_state_id, data):
        GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {})[self.plugin_state[plugin_state_id]['id']] = data

    def ask_set_ranks(self):
        # TODO Make Ctrl-C work - not sure why it isn't --> Check Jamie's pull
        default_text = self.gsdb_get("Ranks").copy()
        default_text[int(self.gsdb_get("Default Rank"))] += "=default"
        default_text.insert(0, "Add named ranks, rename old/autogenerated ranks, and set default rank."
                               "\nThe final and penultimate ranks are reserved for Umpire and Chief of Police")
        return [
            LargeTextEntry(
                title="Rename Ranks",
                identifier=self.html_ids["Ranks"],
                default="\n".join(default_text)
            ),
        ]

    def answer_set_ranks(self, htmlResponse):
        answer = htmlResponse[self.html_ids['Ranks']].split("\n")
        if answer[0] != "Add named ranks, rename old/autogenerated ranks, and set default rank." or answer[1] != "The final and penultimate ranks are reserved for Umpire and Chief of Police":
            return [Label(f"[POLICE] Rename failed - Instructions tampered with")]
        answer.pop(0)
        answer.pop(0)  # To remove the instruction lines. Not sure if they are even necessary, but I think they help
        if len(answer) < 3:
            # TODO check how many ranks minimum are required from event data.
            return [Label(f"[POLICE] Rename failed - Must have enough ranks")]

        default_counter = 0
        for idx, ele in enumerate(answer):
            if ele[-8:] == "=default":
                default_counter += 1
                default = idx
                answer[idx] = ele[:-8]
        if default_counter == 0:
            return [Label(f"[POLICE] Rename failed - No default given")]
        elif default_counter > 1:
            return [Label(f"[POLICE] Rename failed - Too many defaults given")]
        elif default > (len(answer)-3):
            return [Label(f"[POLICE] Rename failed - Umpire/CoP can't be default")]

        self.gsdb_set("Ranks", answer)
        self.gsdb_set("Default Rank", default)
        return [Label(f"[POLICE] Success!")]

    def answer_toggle_auto(self, _):
        self.gsdb_set("Auto Rank", not self.gsdb_get('Auto Rank'))
        return [Label(f"[POLICE] Toggled Auto Ranking from {not self.gsdb_get('Auto Rank')} to {self.gsdb_get('Auto Rank')}")]

    def answer_toggle_manual(self, _):
        self.gsdb_set("Manual Rank", not self.gsdb_get('Manual Rank'))
        return [Label(f"[POLICE] Toggled Manual Ranking from {not self.gsdb_get('Manual Rank')} to {self.gsdb_get('Manual Rank')}")]

    def answer_toggle_police_kills_rankup(self, _):
        self.gsdb_set("Police Kills Rankup", not self.gsdb_get('Police Kills Rankup'))
        return [Label(f"[POLICE] Toggled Auto Ranking on Police Kills from {not self.gsdb_get('Police Kills Rankup')} to {self.gsdb_get('Police Kills Rankup')}")]

    def on_event_request_create(self) -> List[HTMLComponent]:
        # TODO Make a selector with police filtering
        if self.gsdb_get("Manual Rank"):
            return [
                Dependency(
                    dependentOn="CorePlugin_assassin_pseudonym",
                    htmlComponents=[
                        AssassinDependentIntegerEntry(
                            pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                            identifier=self.html_ids["Relative Rank"],
                            title="Select Police to adjust rank (relative to current rank)",
                            default={}
                        )
                    ]
                )
            ]
        else:
            return []

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        if self.gsdb_get("Manual Rank"):
            for player_id, relative_rank in htmlResponse[self.html_ids["Relative Rank"]].items():
                e.pluginState.setdefault(self.identifier, {})[player_id] = relative_rank
            return [Label("[POLICE] Success!")]
        else:
            return [Label("[POLICE] Didn't need to do anything")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        # TODO Make a selector with police filtering
        if self.gsdb_get("Manual Rank"):
            return [
                Dependency(
                    dependentOn="CorePlugin_assassin_pseudonym",
                    htmlComponents=[
                        AssassinDependentIntegerEntry(
                            pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                            identifier=self.html_ids["Relative Rank"],
                            title="Select Police to adjust rank (relative to current rank)",
                            default=e.pluginState.get(self.identifier, {})
                        )
                    ]
                )
            ]
        else:
            return []

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        if self.gsdb_get("Manual Rank"):
            for player_id, relative_rank in htmlResponse[self.html_ids["Relative Rank"]].items():
                e.pluginState.setdefault(self.identifier, {})[player_id] = relative_rank
            return [Label("[POLICE] Success!")]
        else:
            return [Label("[POLICE] Didn't need to do anything")]

    def on_page_generate(self, _) -> List[HTMLComponent]:
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda event: event.datetime)

        police_rank_manager = PoliceRankManager(auto_ranking=self.gsdb_get("Auto Rank"), police_kill_ranking=self.gsdb_get("Police Kills Rankup"))
        death_manager = DeathManager(perma_death=True)
        for e in events:
            police_rank_manager.add_event(e)
            death_manager.add_event(e)

        # Code to generate new ranks if police are promoted/demoted more than ever before
        if police_rank_manager.get_min_rank() < -int(self.gsdb_get("Default Rank")):
            current_ranks = self.gsdb_get("Ranks")
            current_default = int(self.gsdb_get("Default Rank"))
            for i in range(-current_default - police_rank_manager.get_min_rank()):
                current_ranks.insert(0, f"Level {-(i+current_default+1)} Constable")
            self.gsdb_set("Ranks", current_ranks)
            self.gsdb_set("Default Rank", -police_rank_manager.get_min_rank())

        if police_rank_manager.get_max_rank() > (len(self.gsdb_get("Ranks")) - int(self.gsdb_get("Default Rank")) - 3):
            current_ranks = self.gsdb_get("Ranks")
            for i in range(police_rank_manager.get_max_rank() - (len(self.gsdb_get("Ranks")) - self.gsdb_get("Default Rank") - 3)):
                current_ranks.insert(-2, f"Level {len(current_ranks)-2} Constable")
            self.gsdb_set("Ranks", current_ranks)

        police: List[Assassin] = [a for a in ASSASSINS_DATABASE.assassins.values() if a.is_police]
        dead_police: List[Assassin] = [i for i in police if i.identifier in death_manager.get_dead()]
        alive_police: List[Assassin] = [i for i in police if i not in dead_police]
        if GENERIC_STATE_DATABASE.plugin_map.get("WantedPlugin", True):  # i.e. we can separate police into dead and corrupt-dead
            pass
            # TODO after wanted rewrite
            '''
            dead_corrupt_police: List[Assassin] = [i for i in dead_police if i.]
            dead_non_corrupt_police: List[Assassin]
            '''

        tables = []
        if police:
            if alive_police:
                alive_police.sort(key=lambda a: (-int(police_rank_manager.get_relative_rank(a)), a.real_name))
                rows = []
                for a in alive_police:
                    rows.append(
                        POLICE_TABLE_ROW_TEMPLATE.format(
                            RANK=self.gsdb_get("Ranks")[police_rank_manager.get_relative_rank(a)+self.gsdb_get("Default Rank")],
                            PSEUDONYM=a.all_pseudonyms(),
                            NAME=a.real_name,
                            EMAIL=a.email,
                            COLLEGE=a.college,
                            NOTES=a.notes
                        )
                    )
                tables.append(
                    POLICE_TABLE_TEMPLATE.format(ROWS="".join(rows))
                )
            if dead_police:
                dead_police.sort(key=lambda a: (-int(police_rank_manager.get_relative_rank(a)), a.real_name))
                rows = []
                for a in dead_police:
                    rows.append(
                        DEAD_POLICE_TABLE_ROW_TEMPLATE.format(
                            RANK=self.gsdb_get("Ranks")[police_rank_manager.get_relative_rank(a)+self.gsdb_get("Default Rank")],
                            PSEUDONYM=a.all_pseudonyms(),
                            NAME=a.real_name,
                            EMAIL=a.email,
                            COLLEGE=a.college,
                            NOTES=a.notes
                        )
                    )
                tables.append(
                    DEAD_POLICE_TABLE_TEMPLATE.format(ROWS="".join(rows))
                )
            else:
                tables.append(NO_DEAD_POLICE)
        else:
            tables.append(NO_POLICE)

        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "police.html"), "w+") as F:
            F.write(
                POLICE_PAGE_TEMPLATE.format(
                    CONTENT="\n".join(tables),
                    YEAR=datetime.datetime.now().year
                )
            )

        return [Label("[POLICE] Success!")]
