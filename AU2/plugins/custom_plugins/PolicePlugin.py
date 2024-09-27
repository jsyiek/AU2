import datetime
import os
import random
from typing import List

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Assassin, Event
from AU2.html_components import HTMLComponent
from AU2.html_components.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.AssassinDependentSelector import AssassinDependentSelector
from AU2.html_components.AssassinDependentTextEntry import AssassinDependentTextEntry
from AU2.html_components.Dependency import Dependency
from AU2.html_components.InputWithDropDown import InputWithDropDown
from AU2.html_components.IntegerEntry import IntegerEntry
from AU2.html_components.Label import Label
from AU2.html_components.NamedSmallTextbox import NamedSmallTextbox
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export, ConfigExport
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import COLLEGES, WATER_STATUSES, WEBPAGE_WRITE_LOCATION
from AU2.plugins.util import random_data
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.PoliceRankManager import DEFAULT_RANKS, PoliceRankManager

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

POLICE_PAGE_TEMPLATE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "police.html"), "r") as F:
    POLICE_PAGE_TEMPLATE = F.read()

@registered_plugin
class PolicePlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("PolicePlugin")

        self.html_ids = {
            "Rank": self.identifier + "_rank",
            "Rank Name": self.identifier + "_name"
        }

        self.config_exports = [
            ConfigExport(
                "PolicePlugin_set_ranks",
                "Police -> Set Ranks",
                self.ask_set_ranks,
                self.answer_set_ranks
            )
        ]

        self.ranks = GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, DEFAULT_RANKS)

    def ask_set_ranks(self):  # TODO Make Ctrl-C work - not sure why it isn't
        return [
            Label("Rename different ranks of police to fit the game theme"),
            Label("Ranks affect position on the police page, and can be used to reward/punish/just have a bit of fun"),
            InputWithDropDown(
                title="Select rank to rename",
                identifier=self.html_ids["Rank"],
                options=[str(i[0]) + ': ' + i[1] for i in list(GENERIC_STATE_DATABASE.arb_state.get(self.identifier).items())]
            ),
            NamedSmallTextbox(
                title="Enter new name",
                identifier=self.html_ids["Rank Name"],
            )
        ]

    def answer_set_ranks(self, htmlResponse):
        rank = htmlResponse[self.html_ids['Rank']]
        new_name = htmlResponse[self.html_ids['Rank Name']]
        if new_name:
            GENERIC_STATE_DATABASE.arb_state[self.identifier][rank[0]] = new_name
            return [Label(f"[POLICE] Successfully renamed rank {rank} to {new_name}")]
        else:
            return [Label(f"[POLICE] Rename failed - no name given")]

    def on_event_request_create(self) -> List[HTMLComponent]:  # TODO Make a dependent selector, ideally with police filtering
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentTextEntry(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Rank"],
                        title="Change police rank? Must be a number from 0-9",
                        default={}
                    )
                ]
            )
        ]

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})["rank"] = htmlResponse[self.html_ids["Rank"]]
        return [Label("[POLICE] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:  # TODO Make a dependent selector, ideally with police filtering
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentTextEntry(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Rank"],
                        title="Promote police? Must be a number from 0-9",
                        default=e.pluginState.get(self.identifier, {}).get("rank", {}),
                    )
                ]
            )
        ]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})["rank"] = htmlResponse[self.html_ids["Rank"]]
        return [Label("[POLICE] Success!")]

    def on_page_generate(self, htmlResponse) -> List[HTMLComponent]:
        pass
        
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda event: event.datetime)

        police_rank_manager = PoliceRankManager()
        death_manager = DeathManager(perma_death=True)
        for e in events:
            police_rank_manager.add_event(e)
            death_manager.add_event(e)

        police: List[Assassin] = [a for a in ASSASSINS_DATABASE.assassins.values() if a.is_police]
        dead_police: List[Assassin] = [i for i in police if i.identifier in death_manager.get_dead()]
        alive_police: List[Assassin] = [i for i in police if i not in dead_police]
        if GENERIC_STATE_DATABASE.plugin_map.get("WantedPlugin", True):  # i.e. we can separate police into dead and corrupt-dead
            pass  # TODO after wanted rewrite
            '''
            dead_corrupt_police: List[Assassin] = [i for i in dead_police if i.]
            dead_non_corrupt_police: List[Assassin]
            '''

        tables = []
        # Going to assume there are police, because otherwise you wouldn't have this plugin enabled
        if alive_police:
            alive_police.sort(key=lambda a: (-int(police_rank_manager.get_rank(a)), a.real_name))
            rows = []
            print(GENERIC_STATE_DATABASE.arb_state.get(self.identifier))
            for a in alive_police:
                rows.append(
                    POLICE_TABLE_ROW_TEMPLATE.format(
                        RANK=GENERIC_STATE_DATABASE.arb_state.get(self.identifier)[police_rank_manager.get_rank(a)],
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
                dead_police.sort(key=lambda a: (-int(police_rank_manager.get_rank(a)), a.real_name))
                rows = []
                for a in dead_police:
                    rows.append(
                        DEAD_POLICE_TABLE_ROW_TEMPLATE.format(
                            RANK=GENERIC_STATE_DATABASE.arb_state.get(self.identifier)[police_rank_manager.get_rank(a)],
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

            with open(os.path.join(WEBPAGE_WRITE_LOCATION, "police.html"), "w+") as F:
                F.write(
                    POLICE_PAGE_TEMPLATE.format(
                        CONTENT="\n".join(tables),
                        YEAR=datetime.datetime.now().year
                    )
                )

        return [Label("[POLICE] Success!")]
