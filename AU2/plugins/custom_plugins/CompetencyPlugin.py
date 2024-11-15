import datetime
import os
from typing import List

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.DependentComponents.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.DependentComponents.AssassinDependentSelector import AssassinDependentSelector
from AU2.html_components.SimpleComponents.DatetimeEntry import DatetimeEntry
from AU2.html_components.MetaComponents.Dependency import Dependency
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown
from AU2.html_components.SimpleComponents.LargeTextEntry import LargeTextEntry
from AU2.html_components.SimpleComponents.IntegerEntry import IntegerEntry
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.custom_plugins.SRCFPlugin import Email
from AU2.plugins.util.CompetencyManager import ID_GAME_START, ID_DEFAULT_EXTN, DEFAULT_START_COMPETENCY, \
    DEFAULT_EXTENSION, CompetencyManager
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.date_utils import get_now_dt
from AU2.plugins.util.game import get_game_start

INCOS_TABLE_TEMPLATE = """
<p xmlns="">
      This is the list of incompetents:
   </p>
<table xmlns="" class="playerlist">
  <tr><th>Real Name</th><th>Address</th><th>College</th><th>Water Weapons Status</th><th>Notes</th></tr>
  {ROWS}
</table>
"""

INCOS_TABLE_ROW_TEMPLATE = """
<tr><td>{NAME}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{NOTES}</td></tr>
"""

DEAD_INCOS_TABLE_TEMPLATE = """
<p xmlns="">
   	And what follows is a list of corpses:
   </p>
<table xmlns="" class="playerlist">
  <tr><th>Name</th><th>College</th><th>Pseudonym</th></tr>
  {ROWS}
</table>
"""

DEAD_INCOS_TABLE_ROW_TEMPLATE = """
<tr><td>{NAME}</td><td>{COLLEGE}</td><td>{PSEUDONYM}</td></tr>
"""

NO_INCOS = """<p xmlns="">Hmm, how interesting... no one is incompetent yet.</p>"""

DEFAULT_GIGABOLT_HEADLINE = """# Write a headline for the gigabolt event
# Use [num_players] to specify the number of players killed
# Leave this blank for a fully hidden event
# Lines prefixed with # will be ignored
# 
[num_players] assassins are eliminated for inactivity!
"""

INCOS_PAGE_TEMPLATE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "inco.html"), "r", encoding="utf-8", errors="ignore") as F:
    INCOS_PAGE_TEMPLATE = F.read()


@registered_plugin
class CompetencyPlugin(AbstractPlugin):
    FILENAME = "competency.html"
    WRITE_PATH = os.path.join(WEBPAGE_WRITE_LOCATION, FILENAME)
    AUTO_COMPETENCY_OPTIONS = ["Manual", "Auto", "Full Auto"]

    def __init__(self):
        super().__init__("CompetencyPlugin")

        self.html_ids = {
            "Game Start Competency": self.identifier + "_game_start",
            "Default": self.identifier + "_default",
            "Competency": self.identifier + "_competency",
            "Datetime": self.identifier + "_datetime",
            "Auto Competency": self.identifier + "_auto_competency",
            "Attempts": self.identifier + "_attempts",
            "Gigabolt": self.identifier + "_gigabolt",
            "Headline": self.identifier + "_gigabolt_headline",
            "Umpire": self.identifier + "_umpire"
        }

        self.plugin_state = {
            "GAME START": ID_GAME_START,
            "DEFAULT": ID_DEFAULT_EXTN,
            "AUTO COMPETENCY": "auto_competency",
            "ATTEMPT TRACKING": "attempt_tracking",
            "COMPETENCY": "competency",
            "ATTEMPTS": "attempts",
            "CURRENT DEFAULT": "current_default"
        }

        self.exports = [
            Export(
                identifier="competency_plugin_show_deadlines",
                display_name="Competency -> Show deadlines",
                ask=self.ask_show_inco_deadlines,
                answer=self.answer_show_inco_deadlines
            ),
            Export(
                identifier="competency_plugin_gigabolt",
                display_name="Competency -> Gigabolt",
                ask=self.gigabolt_ask,
                answer=self.gigabolt_answer
            )
        ]

        self.config_exports = [
            ConfigExport(
                identifier="competency_plugin_update_competency_defaults",
                display_name="Competency -> Update Default Extension",
                ask=self.set_default_competency_deadline_ask,
                answer=self.set_default_competency_deadline_answer
            ),
            ConfigExport(
                identifier="CompetencyPlugin_auto_competency",
                display_name="Competency -> Change Auto Competency",
                ask=self.ask_auto_competency,
                answer=self.answer_auto_competency
            ),
            ConfigExport(
                identifier="CompetencyPlugin_attempt_tracking",
                display_name="Competency -> Toggle Attempt Tracking",
                ask=lambda *args: [],
                answer=self.answer_toggle_attempt_tracking
            )
        ]

    def gigabolt_ask(self):
        active_players = []
        questions = []
        death_manager = DeathManager()
        if not GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["ATTEMPT TRACKING"]):
            questions.append(Label("[WARNING] Attempt tracking not enabled. Active players may be selected"))
        for e in list(EVENTS_DATABASE.events.values()):
            death_manager.add_event(e)
            for killer, _ in e.kills:
                active_players.append(killer)
            for player_id in e.pluginState.get("CompetencyPlugin", {}).get("attempts", []):
                active_players.append(player_id)
        active_players = set(active_players)

        questions.append(Label("All inactive assassins have been pre-selected"))
        questions.append(Label("Please sanity-check this list - you don't want to eliminate active players"))
        questions.append(SelectorList(
            title="Select assassins to thunderbolt",
            identifier=self.html_ids["Gigabolt"],
            options=[i for i in ASSASSINS_DATABASE.get_identifiers() if not (
                    ASSASSINS_DATABASE.get(i).is_police or death_manager.is_dead(ASSASSINS_DATABASE.get(i)))],
            defaults=[i for i in ASSASSINS_DATABASE.get_identifiers() if not (
                    i in active_players or ASSASSINS_DATABASE.get(i).is_police
                    or death_manager.is_dead(ASSASSINS_DATABASE.get(i)))]
        ))
        questions.append(InputWithDropDown(
            title="Select the umpire, since someone needs to kill the selected players",
            identifier=self.html_ids["Umpire"],
            options=[i for i in ASSASSINS_DATABASE.get_identifiers() if ASSASSINS_DATABASE.get(i).is_police]
            # Will crash if there are no police to choose from
        ))
        questions.append(DatetimeEntry(
            identifier=self.html_ids["Datetime"],
            title="Enter date/time of event")
        )
        questions.append(LargeTextEntry(
            identifier=self.html_ids["Headline"],
            title="Headline",
            default=DEFAULT_GIGABOLT_HEADLINE)
        )

        return questions

    def gigabolt_answer(self, htmlResponse):
        deaths = htmlResponse[self.html_ids['Gigabolt']]
        umpire = htmlResponse[self.html_ids['Umpire']]
        # remove lines beginning with '#'
        headline = '\n'.join([i for i in htmlResponse[self.html_ids['Headline']].split('\n') if not i.startswith('#')])
        headline = headline.replace('[num_players]', str(len(deaths)))
        # TODO Adjust targeting plugin so that it can handle events with many deaths, by retargeting in chunks
        # I don't want to mess with the targeting plugin mid-game, so making a bunch of events with n kills each works for now
        # Number of deaths per event:
        n = 3
        # Brief testing showed that 5 was too large (and broke targeting). 1 makes an annoying number of events
        subdivided_deaths = [deaths[i:i + n] for i in range(0, len(deaths), n)]
        for idx, i in enumerate(subdivided_deaths):
            EVENTS_DATABASE.add(
                Event(
                    assassins={j: 0 for j in i} | {umpire: 0},
                    datetime=htmlResponse[self.html_ids['Datetime']],
                    headline=f"Gigabolt stage {idx+1}" if (idx or not headline) else headline,
                    reports={},
                    kills=[(umpire, j) for j in i],
                    pluginState={"PageGeneratorPlugin": {"hidden_event": idx or not headline}}
                )
            )

        return [Label(f"[COMPETENCY] Gigabolt Success! {len(deaths)} players eliminated")]

    def set_default_competency_deadline_ask(self):
        return [
            Label("Competency periods begin automatically from game start."),
            IntegerEntry(
                title="Enter competency granted at game start",
                identifier=self.html_ids["Game Start Competency"],
                default=GENERIC_STATE_DATABASE.arb_int_state.get(self.plugin_state["GAME START"], DEFAULT_START_COMPETENCY)
            ),
            IntegerEntry(
                title="Enter default competency extension",
                identifier=self.html_ids["Default"],
                default=GENERIC_STATE_DATABASE.arb_int_state.get(self.plugin_state["DEFAULT"], DEFAULT_EXTENSION)
            )
        ]

    def set_default_competency_deadline_answer(self, htmlResponse):
        new_game_start = htmlResponse[self.html_ids['Game Start Competency']]
        new_val = htmlResponse[self.html_ids['Default']]
        GENERIC_STATE_DATABASE.arb_int_state[self.plugin_state["GAME START"]] = new_game_start
        GENERIC_STATE_DATABASE.arb_int_state[self.plugin_state["DEFAULT"]] = new_val
        return [Label(f"[COMPETENCY] Updated game start to {new_game_start} and extension to {new_val}")]

    def answer_toggle_attempt_tracking(self, _):
        new_state = not GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["ATTEMPT TRACKING"], False)
        GENERIC_STATE_DATABASE.arb_state[self.plugin_state["ATTEMPT TRACKING"]] = new_state
        return [Label(f"[COMPETENCY] Toggled attempt tracking to {new_state}")]

    def ask_auto_competency(self):
        return [
            InputWithDropDown(
                identifier=self.html_ids["Auto Competency"],
                title="Select Auto Competency Mode",
                options=self.AUTO_COMPETENCY_OPTIONS,
                selected=GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["AUTO COMPETENCY"], "Manual")
            )
        ]

    def answer_auto_competency(self, htmlResponse):
        mode = htmlResponse[self.html_ids["Auto Competency"]]
        GENERIC_STATE_DATABASE.arb_state[self.plugin_state["AUTO COMPETENCY"]] = mode
        response = [Label(f"[COMPETENCY] Auto Competency Mode set to {mode}")]
        if mode != "Manual" and not GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["ATTEMPT TRACKING"], False):
            response.append(
                Label(f"[COMPETENCY] Warning: Attempt Tracking not enabled. Attempt competency must be added manually")
            )
        return response

    def on_hook_respond(self, hook: str, htmlResponse, data) -> List[HTMLComponent]:
        if hook == "SRCFPlugin_email":
            events = list(EVENTS_DATABASE.events.values())
            events.sort(key=lambda event: event.datetime)

            competency_manager = CompetencyManager(get_game_start())
            death_manager = DeathManager()
            for e in events:
                competency_manager.add_event(e)
                death_manager.add_event(e)

            now = get_now_dt()
            email_list: List[Email] = data
            for email in email_list:
                recipient = email.recipient
                if recipient.is_police:
                    continue
                if competency_manager.is_inco_at(recipient, now):
                    content = "It would seem you've become incompetent. You might wish to change that.\nIn order to " \
                              "regain competency, you must make a kill, or two attempted kills, or assist two " \
                              "attempts by another (or some combination thereof)."
                else:
                    deadline_str = competency_manager.deadlines[recipient.identifier].strftime("%Y-%m-%d %H:%M")
                    content = f"Your competence deadline is at: {deadline_str}"
                email.add_content(
                    self.identifier,
                    content=content,
                    require_send=False
                )
        return []

    def on_event_request_create(self) -> List[HTMLComponent]:
        questions = []
        if GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["AUTO COMPETENCY"], "Manual") != "Full Auto":
            questions.append(
                Dependency(
                    dependentOn="CorePlugin_assassin_pseudonym",
                    htmlComponents=[
                        AssassinDependentIntegerEntry(
                            pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                            identifier=self.html_ids["Competency"],
                            title="Extend competency?",
                            default={},
                            global_default=GENERIC_STATE_DATABASE.arb_int_state.get(self.plugin_state["DEFAULT"], DEFAULT_EXTENSION)
                        )
                    ]
                )
            )
        if GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["ATTEMPT TRACKING"], False):
            questions.append(
                Dependency(
                    dependentOn="CorePlugin_assassin_pseudonym",
                    htmlComponents=[
                        AssassinDependentSelector(
                            pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                            identifier=self.html_ids["Attempts"],
                            title="Select players who made an attempt or assist",
                        )
                    ]
                )
            )
        return questions

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        if self.html_ids["Competency"] in htmlResponse:
            e.pluginState.setdefault(self.identifier, {})[self.plugin_state["COMPETENCY"]] = htmlResponse[self.html_ids["Competency"]]
        if self.html_ids["Attempts"] in htmlResponse:
            e.pluginState.setdefault(self.identifier, {})[self.plugin_state["ATTEMPTS"]] = htmlResponse[self.html_ids["Attempts"]]
        # Store the default competency extension at the time of the event, in the event
        # This way auto competency can be calculated dynamically
        e.pluginState.setdefault(self.identifier, {})[self.plugin_state["CURRENT DEFAULT"]] = \
            GENERIC_STATE_DATABASE.arb_int_state.get(self.plugin_state["DEFAULT"], DEFAULT_EXTENSION)
        return [Label("[COMPETENCY] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        # Allow competency editing on event update even if full auto competency enabled.
        # TODO Make a selector that pre-filters to non-police players
        questions = [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentIntegerEntry(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Competency"],
                        title="Extend competency?",
                        default=e.pluginState.get(self.identifier, {}).get(self.plugin_state["COMPETENCY"], {}),
                        global_default=GENERIC_STATE_DATABASE.arb_int_state.get(self.plugin_state["DEFAULT"], DEFAULT_EXTENSION)
                    )
                ]
            )
        ]
        if GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["ATTEMPT TRACKING"], False):
            questions.append(
                Dependency(
                    dependentOn="CorePlugin_assassin_pseudonym",
                    htmlComponents=[
                        AssassinDependentSelector(
                            pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                            identifier=self.html_ids["Attempts"],
                            title="Select players who made an attempt or assist",
                            default=e.pluginState.get(self.identifier, {}).get(self.plugin_state["ATTEMPTS"], {}),
                        )
                    ]
                )
            )
        return questions

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})[self.plugin_state["COMPETENCY"]] = htmlResponse[self.html_ids["Competency"]]
        if self.html_ids["Attempts"] in htmlResponse:
            e.pluginState.setdefault(self.identifier, {})[self.plugin_state["ATTEMPTS"]] = htmlResponse[self.html_ids["Attempts"]]
        return [Label("[COMPETENCY] Success!")]

    def on_page_request_generate(self) -> List[HTMLComponent]:
        return [DatetimeEntry(
            identifier=self.html_ids["Datetime"],
            title="Enter date to calculate incos from"
        )]

    def ask_show_inco_deadlines(self):
        return []

    def answer_show_inco_deadlines(self, _):
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda event: event.datetime)
        start_datetime: datetime.datetime = get_game_start()

        competency_manager = CompetencyManager(start_datetime)
        death_manager = DeathManager(perma_death=True)

        for e in events:
            competency_manager.add_event(e)
            death_manager.add_event(e)

        deadlines = []
        for a in ASSASSINS_DATABASE.get_identifiers():
            deadlines.append((a, competency_manager.get_deadline_for(ASSASSINS_DATABASE.assassins[a])))
            if "jackson" in a.lower(): # ????
                competency_manager.is_inco_at(ASSASSINS_DATABASE.assassins[a], get_now_dt())
        deadlines.sort(key=lambda t: t[1])

        labels = []

        DATETIME_FORMAT = "%Y-%m-%d %H:%M"

        labels.append(Label("__________________________________________________________________"))

        for (a, d) in deadlines:
            labels.append(Label(f"{a} -> {datetime.datetime.strftime(d, DATETIME_FORMAT)}"))
            labels.append(Label("__________________________________________________________________"))
        return labels

    def on_page_generate(self, htmlResponse) -> List[HTMLComponent]:
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda event: event.datetime)
        start_datetime: datetime.datetime = get_game_start()

        competency_manager = CompetencyManager(start_datetime)
        death_manager = DeathManager(perma_death=True)
        limit = htmlResponse[self.html_ids["Datetime"]]
        for e in events:
            if e.datetime > limit:
                break
            competency_manager.add_event(e)
            death_manager.add_event(e)

        incos = competency_manager.get_incos_at(limit)
        dead_incos: List[Assassin] = [i for i in incos if i.identifier in death_manager.get_dead()]
        alive_incos: List[Assassin] = [i for i in incos if i not in dead_incos]

        tables = []
        if alive_incos:
            alive_incos.sort(key=lambda a: (a.college, a.real_name))
            rows = []
            for a in alive_incos:
                rows.append(
                    INCOS_TABLE_ROW_TEMPLATE.format(
                        NAME=a.real_name,
                        ADDRESS=a.address,
                        COLLEGE=a.college,
                        WATER_STATUS=a.water_status,
                        NOTES=a.notes
                    )
                )
            tables.append(
                INCOS_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )

        # TODO: Disabled until logic for dead incos is repaired
        if dead_incos and False:
            dead_incos.sort(key=lambda a: (a.college, a.real_name))
            rows = []
            for a in dead_incos:
                rows.append(
                    DEAD_INCOS_TABLE_ROW_TEMPLATE.format(
                        NAME=a.real_name,
                        COLLEGE=a.college,
                        PSEUDONYM=a.all_pseudonyms()
                    )
                )
            tables.append(
                DEAD_INCOS_TABLE_TEMPLATE.format(ROWS="".join(rows))
            )

        if not tables:
            tables = [NO_INCOS]

        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "inco.html"), "w+", encoding="utf-8") as F:
            F.write(
                INCOS_PAGE_TEMPLATE.format(
                    CONTENT="\n".join(tables),
                    YEAR=get_now_dt().year
                )
            )

        return [Label("[COMPETENCY] Success!")]
