import os
from typing import List, Dict

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Assassin, Event
from AU2.html_components import HTMLComponent
from AU2.html_components.DependentComponents.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.MetaComponents.Dependency import Dependency
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.LargeTextEntry import LargeTextEntry
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.NamedSmallTextbox import NamedSmallTextbox
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.PoliceRankManager import DEFAULT_RANKS, PoliceRankManager, DEFAULT_POLICE_RANK, AUTO_RANK_DEFAULT, \
    MANUAL_RANK_DEFAULT, POLICE_KILLS_RANKUP_DEFAULT
from AU2.plugins.util.date_utils import get_now_dt, DATETIME_FORMAT
from AU2.plugins.util.render_utils import event_url

POLICE_TABLE_TEMPLATE = """
<p xmlns="">
    Here is a list of members of our loyal city watch, charged with protecting Cambridge from murderers of innocents and people that annoy the all powerful Umpire:
</p>
<table xmlns="" class="playerlist">
  <tr><th>Rank</th><th>Pseudonym</th><th>Real Name</th><th>Email Address</th><th>College</th><th>Notes</th><th>Deaths</th></tr>
  {ROWS}
</table>
"""

POLICE_TABLE_ROW_TEMPLATE = """
<tr><td>{RANK}</td><td>{PSEUDONYM}</td><td>{NAME}</td><td>{EMAIL}</td><td>{COLLEGE}</td><td>{NOTES}</td><td>{DEATHS}</td></tr>
"""

NO_POLICE = """<p xmlns="">The city watch is suspiciously understaffed at the moment.</p>"""


POLICE_PAGE_TEMPLATE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "police.html"), "r", encoding="utf-8", errors="ignore") as F:
    POLICE_PAGE_TEMPLATE = F.read()


@registered_plugin
class CityWatchPlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("CityWatchPlugin")

        self.html_ids = {
            "Ranks": self.identifier + "_ranks",
            "Relative Rank": self.identifier + "_rank_relative",
            "Options": self.identifier + "_options",
            "Umpires": self.identifier + "_umpires",
            "CoP": self.identifier + "_cop",
            "Assassin": self.identifier + "_assassin",
            "Pseudonym": self.identifier + "_pseudonym"
        }

        self.plugin_state = {
            "Ranks": {'id': self.identifier + "_ranks", 'default': DEFAULT_RANKS},  # List
            "Default Rank": {'id': self.identifier + "_default_rank", 'default': DEFAULT_POLICE_RANK},  # Int
            "Auto Rank": {'id': self.identifier + "_auto_rank", 'default': AUTO_RANK_DEFAULT},  # Bool
            "Manual Rank": {'id': self.identifier + "_manual_rank", 'default': MANUAL_RANK_DEFAULT},  # Bool
            "City Watch Kills Rankup": {'id': self.identifier + "_police_kills_rankup", 'default': POLICE_KILLS_RANKUP_DEFAULT},  # Bool
            "Umpires": {'id': self.identifier + "_umpires", 'default': []},
            "Chief of Police": {'id': self.identifier + "_cop", 'default': []},
        }

        self.exports = [
            Export(
                "police_plugin_assassin_to_police",
                "Assassin -> Resurrect as City Watch",
                self.ask_resurrect_as_police,
                self.answer_resurrect_as_police,
                (self.gather_dead_non_police,)
            ),
        ]

        self.config_exports = [
            ConfigExport(
                identifier="police_plugin_set_ranks",
                display_name="City Watch -> Set Ranks",
                ask=self.ask_set_ranks,
                answer=self.answer_set_ranks
            ),
            ConfigExport(
                identifier="police_plugin_select_options",
                display_name="City Watch -> Select Ranking options",
                ask=self.ask_select_options,
                answer=self.answer_select_options
            ),
            ConfigExport(
                identifier="police_plugin_set_special_ranks",
                display_name="City Watch -> Set Umpire(s)/Commander(s) of the Watch",
                ask=self.ask_set_special_ranks,
                answer=self.answer_set_special_ranks
            )
        ]
    # configs are only stored in database if changed; otherwise the hardcoded default configs are used.

    def gsdb_get(self, plugin_state_id):
        return GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get(self.plugin_state[plugin_state_id]['id'],
                                                                             self.plugin_state[plugin_state_id]['default'])

    def gsdb_set(self, plugin_state_id, data):
        GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {})[self.plugin_state[plugin_state_id]['id']] = data

    def on_request_setup_game(self, game_type: str) -> List[HTMLComponent]:
        return [
            *self.ask_set_special_ranks(),
        ]

    def on_setup_game(self, htmlResponse) -> List[HTMLComponent]:
        return [
            *self.answer_set_special_ranks(htmlResponse),
        ]

    def gather_dead_non_police(self) -> List[str]:
        death_manager = DeathManager()
        for e in EVENTS_DATABASE.events.values():
            death_manager.add_event(e)
        return ASSASSINS_DATABASE.get_identifiers(include=(lambda a: death_manager.is_dead(a) and not a.is_police))

    def ask_resurrect_as_police(self, ident: str):
        components = [HiddenTextbox(identifier=self.html_ids["Assassin"], default=ident),
                      NamedSmallTextbox(identifier=self.html_ids["Pseudonym"], title="New initial pseudonym")]
        return components

    # TODO: make resurrection a hook, so that plugins can decide what to do with plugin data stored in assassins
    #       current behaviour is to copy it over.
    def answer_resurrect_as_police(self, html_response_args: Dict):
        ident = html_response_args[self.html_ids["Assassin"]]
        assassin = ASSASSINS_DATABASE.get(ident)
        new_pseudonym = html_response_args[self.html_ids["Pseudonym"]]
        new_assassin = assassin.clone(hidden=False, is_police=True, pseudonyms=[new_pseudonym], pseudonym_datetimes={})
        ASSASSINS_DATABASE.add(new_assassin)
        # hide the old assassin
        assassin.hidden = True
        return [Label(f"[CITY WATCH] Resurrected {ident} as {new_assassin.identifier}.")]

    def ask_set_special_ranks(self):
        all_police = [a.identifier for a in ASSASSINS_DATABASE.assassins.values() if a.is_police]
        return [
            Label("This only affects the displayed rank on the website"),
            SelectorList(
                title="Select the Umpire(s)",
                identifier=self.html_ids["Umpires"],
                options=all_police,
                defaults=self.gsdb_get("Umpires")
            ),
            SelectorList(
                title="Select the Commander(s) of the Watch",
                identifier=self.html_ids["CoP"],
                options=all_police,
                defaults=self.gsdb_get("Chief of Police")
            )
        ]

    def answer_set_special_ranks(self, htmlResponse):
        self.gsdb_set("Umpires", htmlResponse[self.html_ids["Umpires"]])
        self.gsdb_set("Chief of Police", htmlResponse[self.html_ids["CoP"]])
        return [Label("[CITY WATCH] Successfully set Umpire(s) and Commander(s) of the Watch")]

    def ask_set_ranks(self):
        question = []
        default_text = self.gsdb_get("Ranks").copy()
        if int(self.gsdb_get("Default Rank")) not in range(len(default_text)-2):
            self.gsdb_set("Default Rank", 0)
            question.append(Label("Default Rank in database broken, and has been reset to 0"))
        default_text[int(self.gsdb_get("Default Rank"))] += "=default"
        default_text.insert(0, "# Add named ranks, rename old/autogenerated ranks, and set default rank."
                               "\n# The final and penultimate ranks are reserved for Umpire and Chief of Police."
                               "\n# Lines beginning with # are ignored.")
        question.append(LargeTextEntry(
                title="Rename Ranks",
                identifier=self.html_ids["Ranks"],
                default="\n".join(default_text)
            ))
        return question

    def answer_set_ranks(self, htmlResponse):
        answer = htmlResponse[self.html_ids['Ranks']].split("\n")
        answer = (i.strip() for i in answer)
        answer = [i for i in answer if i and not i.startswith('#')]
        if len(answer) < 3:
            return [Label("[CITY WATCH] Rename failed - Must have enough ranks")]

        default_counter = 0
        for idx, ele in enumerate(answer):
            if ele.endswith("=default"):
                default_counter += 1
                default = idx
                answer[idx] = ele[:-8]
        if default_counter == 0:
            default = 0
        elif default_counter > 1:
            return [Label("[CITY WATCH] Rename failed - Too many defaults given")]
        elif default > (len(answer)-3):
            return [Label("[CITY WATCH] Rename failed - Umpire/Commander of the Watch can't be default rank")]

        self.gsdb_set("Ranks", answer)
        self.gsdb_set("Default Rank", default)
        return [Label("[CITY WATCH] Success!")]

    def ask_select_options(self):
        toggles = ["Manual Rank", "Auto Rank", "City Watch Kills Rankup"]
        return [
            SelectorList(
                title="Select ranking options",
                identifier=self.html_ids["Options"],
                options=toggles,
                defaults=[t for t in toggles if self.gsdb_get(t)]
            ),
        ]

    def answer_select_options(self, htmlResponse):
        answer = htmlResponse[self.html_ids["Options"]]
        toggles = ["Manual Rank", "Auto Rank", "City Watch Kills Rankup"]
        for i in toggles:
            self.gsdb_set(i, i in answer)
        return [Label("[CITY WATCH] Success!")]

    def on_event_request_create(self) -> List[HTMLComponent]:
        # TODO Make a selector with police filtering
        if not self.gsdb_get("Manual Rank"):
            return []
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentIntegerEntry(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Relative Rank"],
                        title="Select players to adjust City Watch rank (relative to current rank)",
                        default={}
                    )
                ]
            )
        ]

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        if not self.gsdb_get("Manual Rank"):
            return [Label("[CITY WATCH] Didn't need to do anything")]

        for player_id, relative_rank in htmlResponse[self.html_ids["Relative Rank"]].items():
            e.pluginState.setdefault(self.identifier, {})[player_id] = relative_rank
        return [Label("[CITY WATCH] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        # TODO Make a selector with police filtering
        if not self.gsdb_get("Manual Rank"):
            return []
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentIntegerEntry(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Relative Rank"],
                        title="Select players to adjust City Watch rank (relative to current rank)",
                        default=e.pluginState.get(self.identifier, {})
                    )
                ]
            )
        ]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        if not self.gsdb_get("Manual Rank"):
            return [Label("[CITY WATCH] Didn't need to do anything")]

        for player_id, relative_rank in htmlResponse[self.html_ids["Relative Rank"]].items():
            e.pluginState.setdefault(self.identifier, {})[player_id] = relative_rank
        return [Label("[CITY WATCH] Success!")]

    def on_page_generate(self, _) -> List[HTMLComponent]:
        message = []
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda event: event.datetime)

        police_rank_manager = PoliceRankManager(auto_ranking=self.gsdb_get("Auto Rank"), police_kill_ranking=self.gsdb_get("City Watch Kills Rankup"))
        death_manager = DeathManager()
        for e in events:
            police_rank_manager.add_event(e)
            death_manager.add_event(e)

        message += police_rank_manager.generate_new_ranks_if_necessary()

        # note: police who are hidden using `Assassin -> Hide` will not be included
        police: List[Assassin] = ASSASSINS_DATABASE.get_filtered(include=lambda a: a.is_police)

        tables = []
        if police:
            police.sort(key=lambda a: (-int(police_rank_manager.get_relative_rank(a.identifier)), a.real_name))
            rows = []
            for a in police:
                deaths = [f'<a href="{event_url(e)}">{e.datetime.strftime(DATETIME_FORMAT)}</a>'
                          for e in death_manager.get_death_events(a)]
                rows.append(
                    POLICE_TABLE_ROW_TEMPLATE.format(
                        RANK=police_rank_manager.get_rank_name(a.identifier),
                        PSEUDONYM=a.all_pseudonyms(),
                        NAME=a.real_name,
                        EMAIL=a.email,
                        COLLEGE=a.college,
                        NOTES=a.notes,
                        DEATHS='<br />'.join(deaths) if deaths else "&mdash;",
                    )
                )
            tables.append(
                POLICE_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )
        else:
            tables.append(NO_POLICE)

        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "citywatch.html"), "w+", encoding="utf-8", errors="ignore") as F:
            F.write(
                POLICE_PAGE_TEMPLATE.format(
                    CONTENT="\n".join(tables),
                    YEAR=get_now_dt().year
                )
            )
        message.append(Label("[CITY WATCH] Success!"))
        return message
