import datetime
import os
from typing import List

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.AssassinDependentSelector import AssassinDependentSelector
from AU2.html_components.DatetimeEntry import DatetimeEntry
from AU2.html_components.Dependency import Dependency
from AU2.html_components.InputWithDropDown import InputWithDropDown
from AU2.html_components.IntegerEntry import IntegerEntry
from AU2.html_components.Label import Label
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
            "Attempts": self.identifier + "_attempts"
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

        self.config_exports = [
            ConfigExport(
                identifier="CompetencyPlugin_update_competency_defaults",
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
            events = EVENTS_DATABASE.events
            competency_manager = CompetencyManager(game_start=get_game_start())
            death_manager = DeathManager()
            for e in events.values():
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

    def on_page_generate(self, htmlResponse) -> List[HTMLComponent]:
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda event: event.datetime)
        start_datetime: datetime.datetime = get_game_start()
        auto_competency_bool = GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["AUTO COMPETENCY"], "Manual") != "Manual"

        competency_manager = CompetencyManager(start_datetime, auto_competency_bool)
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
        if dead_incos:
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

        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "inco.html"), "w+") as F:
            F.write(
                INCOS_PAGE_TEMPLATE.format(
                    CONTENT="\n".join(tables),
                    YEAR=get_now_dt().year
                )
            )

        return [Label("[COMPETENCY] Success!")]
