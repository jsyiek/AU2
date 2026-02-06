import dataclasses
import datetime
import enum
import os
from typing import Any, Dict, List, Set

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.DependentComponents.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.DatetimeEntry import DatetimeEntry
from AU2.html_components.MetaComponents.Dependency import Dependency
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown
from AU2.html_components.SimpleComponents.LargeTextEntry import LargeTextEntry
from AU2.html_components.SimpleComponents.IntegerEntry import IntegerEntry
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.html_components.SimpleComponents.Table import Table
from AU2.html_components.SimpleComponents.NamedSmallTextbox import NamedSmallTextbox
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport, Export, DangerousConfigExport, \
    AttributePairTableRow
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.custom_plugins.SRCFPlugin import Email
from AU2.plugins.util.CompetencyManager import ID_GAME_START, ID_DEFAULT_EXTN, DEFAULT_START_COMPETENCY, \
    DEFAULT_EXTENSION, CompetencyManager
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.date_utils import get_now_dt, DATETIME_FORMAT
from AU2.plugins.util.game import get_game_start, get_game_end

INCOS_TABLE_TEMPLATE = """
<p xmlns="">
      This is the list of incompetents:
   </p>
<table xmlns="" class="playerlist">
  <tr><th>Real Name</th><th>Address</th><th>College</th><th>Room Water Weapons Status</th><th>Notes</th></tr>
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


class PlayerStatus(enum.Enum):
    COMPETENT = enum.auto()
    CITY_WATCH = enum.auto()
    INCOMPETENT = enum.auto()
    GIGAINCOMPETENT = enum.auto()
    DEAD = enum.auto()

    def is_alive_player(self):
        """
        Returns true if this player status represents a player that is alive
        """
        return self in [self.COMPETENT, self.INCOMPETENT, self.GIGAINCOMPETENT]

    def __str__(self):
        return str(self.name).replace("PlayerStatus.", "")


@dataclasses.dataclass
class PlayerInfo:
    identifier: str
    status: PlayerStatus
    competency_deadline: datetime.datetime


def get_active_players(death_manager: DeathManager) -> Set[str]:
    """
    Collects all players not currently at risk of a gigabolt
    """
    active_players = []

    for e in sorted(list(EVENTS_DATABASE.events.values()), key=lambda event: event.datetime):
        death_manager.add_event(e)
        for killer, _ in e.kills:
            active_players.append(killer)
        for player_id in e.pluginState.get("CompetencyPlugin", {}).get("attempts", []):
            active_players.append(player_id)
    return set(active_players)


def get_player_infos(from_date=get_now_dt()) -> Dict[str, PlayerInfo]:
    """
    Returns a list of calculated player informations (see struct above)
    """
    events = list(EVENTS_DATABASE.events.values())
    events.sort(key=lambda event: event.datetime)
    start_datetime: datetime.datetime = get_game_start()

    competency_manager = CompetencyManager(start_datetime)
    death_manager = DeathManager()

    # populates the death manager
    active_players = get_active_players(death_manager)

    for e in events:
        competency_manager.add_event(e)

    infos = {}
    for a in ASSASSINS_DATABASE.get_filtered(include_hidden=lambda _: True):
        status = PlayerStatus.COMPETENT
        is_gigainco = a.identifier not in active_players
        is_inco = competency_manager.is_inco_at(a, from_date)
        is_dead = death_manager.is_dead(a)

        # Ordering of the below is important - don't reorder!
        if a.is_city_watch:
            status = PlayerStatus.CITY_WATCH
        elif is_dead:
            status = PlayerStatus.DEAD
        elif is_gigainco:
            status = PlayerStatus.GIGAINCOMPETENT
        elif is_inco:
            status = PlayerStatus.INCOMPETENT
        infos[a.identifier] = PlayerInfo(
            identifier=a.identifier,
            status=status,
            competency_deadline=competency_manager.get_deadline_for(a)
        )
    return infos


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
            "Attempt Tracking": self.identifier + "_attempt_tracking",
            "Attempts": self.identifier + "_attempts",
            "Gigabolt": self.identifier + "_gigabolt",
            "Headline": self.identifier + "_gigabolt_headline",
            "Umpire": self.identifier + "_umpire",
            "Search": self.identifier + "_search"
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

        Assassin.__last_emailed_competency = self.assassin_property("last_emailed_competency", None, store_default=False)

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
            DangerousConfigExport(
                identifier="CompetencyPlugin_auto_competency",
                display_name="Competency -> Change Auto Competency",
                ask=self.ask_auto_competency,
                answer=self.answer_auto_competency,
                danger_explanation=self.auto_competency_danger_explanation
            ),
            ConfigExport(
                identifier="CompetencyPlugin_attempt_tracking",
                display_name="Competency -> Toggle Attempt Tracking",
                ask=self.ask_toggle_attempt_tracking,
                answer=self.answer_toggle_attempt_tracking
            )
        ]

    def on_request_setup_game(self, game_type: str) -> List[HTMLComponent]:
        # don't ask about auto-competency or attempt tracking because we'll just default these to on
        # and changing these would only be helpful to someone who has a good idea of what they're doing
        return [
            *self.set_default_competency_deadline_ask(),
        ]

    def on_setup_game(self, htmlResponse) -> List[HTMLComponent]:
        return [
            *self.set_default_competency_deadline_answer(htmlResponse),
        ]

    def gigabolt_ask(self):
        questions = []

        questions.append(Label("All inactive assassins have been pre-selected"))
        questions.append(Label("[WARNING] This selection will only be accurate if attempts have been correctly tracked."))
        questions.append(Label("Please sanity-check this list - you don't want to eliminate active players"))

        death_manager = DeathManager()
        active_players = get_active_players(death_manager)
        available_assassins = ASSASSINS_DATABASE.get_identifiers(include=lambda a: not (a.is_city_watch or death_manager.is_dead(a)))
        questions.append(SelectorList(
            title="Select assassins to thunderbolt",
            identifier=self.html_ids["Gigabolt"],
            options=available_assassins,
            defaults=[i for i in available_assassins if not i in active_players]
        ))
        questions.append(InputWithDropDown(
            title="Select the umpire, since someone needs to kill the selected players",
            identifier=self.html_ids["Umpire"],
            options=[i for i in ASSASSINS_DATABASE.get_identifiers() if ASSASSINS_DATABASE.get(i).is_city_watch],
            selected=GENERIC_STATE_DATABASE.arb_state.get("CityWatchPlugin", {}).get("CityWatchPlugin_umpires", [""])[0]
            # Will crash if there are no city watch to choose from
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
                    pluginState={"PageGeneratorPlugin": {"hidden_event": bool(idx) or not headline}}
                )
            )

        return [Label(f"[COMPETENCY] Gigabolt Success! {len(deaths)} players eliminated")]

    def set_default_competency_deadline_ask(self):
        return [
            Label("Competency periods begin automatically from game start."),
            IntegerEntry(
                title="Enter competency granted at game start (in days)",
                identifier=self.html_ids["Game Start Competency"],
                default=GENERIC_STATE_DATABASE.arb_int_state.get(self.plugin_state["GAME START"], DEFAULT_START_COMPETENCY)
            ),
            IntegerEntry(
                title="Enter default competency extension (in days)",
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

    def ask_auto_competency(self):
        return [
            InputWithDropDown(
                identifier=self.html_ids["Auto Competency"],
                title="Select Auto Competency Mode",
                options=self.AUTO_COMPETENCY_OPTIONS,
                selected=GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["AUTO COMPETENCY"], "Auto")
            )
        ]

    def answer_auto_competency(self, htmlResponse):
        mode = htmlResponse[self.html_ids["Auto Competency"]]
        GENERIC_STATE_DATABASE.arb_state[self.plugin_state["AUTO COMPETENCY"]] = mode
        response = [Label(f"[COMPETENCY] Auto Competency Mode set to {mode}")]
        if mode != "Manual" and not GENERIC_STATE_DATABASE.arb_state.setdefault(self.plugin_state["ATTEMPT TRACKING"], True):
            response.append(
                Label("[COMPETENCY] Warning: Attempt Tracking not enabled. Attempt competency must be added manually.")
            )
        return response

    def auto_competency_danger_explanation(self) -> str:
        if GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["AUTO COMPETENCY"], "Auto") != "Manual":
            return "Auto competency is enabled. It is inadvisable to disable it."
        else:
            return ""

    def ask_toggle_attempt_tracking(self) -> List[HTMLComponent]:
        return [
            Checkbox(
                identifier=self.html_ids["Attempt Tracking"],
                title="Track attempts/assists?",
                checked=GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["ATTEMPT TRACKING"], True)
            )
        ]

    def answer_toggle_attempt_tracking(self, htmlResponse) -> List[HTMLComponent]:
        track_attempts = htmlResponse[self.html_ids["Attempt Tracking"]]
        GENERIC_STATE_DATABASE.arb_state[self.plugin_state["ATTEMPT TRACKING"]] = track_attempts
        manual = GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["AUTO COMPETENCY"], "Auto")  == "Manual"

        response = [Label(f"[COMPETENCY] Attempt tracking has been {'en' if track_attempts else 'dis'}abled.")]
        if not track_attempts and not manual:
            response.append(
                Label("[COMPETENCY] Note: Any previously recorded attempts/assists will still contribute to auto-competency.")
            )
        elif track_attempts and manual:
            response.append(
                Label("[COMPETENCY] Warning: Manual competency is enabled. Attempt competency must be added manually.")
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
                if recipient.is_city_watch or death_manager.is_dead(recipient):
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
                    require_send=recipient.__last_emailed_competency != competency_manager.deadlines[recipient.identifier]
                )

                # only record emailed competency if emails will actually be sent
                # the component is named confusingly. here, True = *do* send emails!
                # TODO: would be good to be able to do this *after* emails sent...
                if htmlResponse.get("SRCFPlugin_dry_run", True):
                    recipient.__last_emailed_competency = competency_manager.deadlines[recipient.identifier]

        return []

    def on_event_request_create(self) -> List[HTMLComponent]:
        questions = []
        if GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["ATTEMPT TRACKING"], True):
            questions.append(
                Dependency(
                    dependentOn="CorePlugin_assassin_pseudonym",
                    htmlComponents=[
                        AssassinDependentIntegerEntry(
                            pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                            identifier=self.html_ids["Attempts"],
                            title="Add attempts/assists",
                            default={},
                            global_default=1
                        )
                    ]
                )
            )
        mode = GENERIC_STATE_DATABASE.arb_state.setdefault(self.plugin_state["AUTO COMPETENCY"], "Auto")
        if mode != "Full Auto":
            questions.append(
                Dependency(
                    dependentOn="CorePlugin_assassin_pseudonym",
                    htmlComponents=[
                        AssassinDependentIntegerEntry(
                            pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                            identifier=self.html_ids["Competency"],
                            title="Manually extend competency?" if mode != "Manual" else "Extend competency?",
                            default={},
                            global_default=GENERIC_STATE_DATABASE.arb_int_state.get(self.plugin_state["DEFAULT"], DEFAULT_EXTENSION)
                        )
                    ]
                )
            )
        return questions

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        if self.html_ids["Competency"] in htmlResponse:
            e.pluginState.setdefault(self.identifier, {})[self.plugin_state["COMPETENCY"]] = htmlResponse[self.html_ids["Competency"]]
        if self.html_ids["Attempts"] in htmlResponse:
            # This currently stores attempts as ['a', 'a'] for two attempts by player a
            # It would be better to store as a dict {'a':2}, but I can't break the current database
            # TODO cleanup after game end
            e.pluginState.setdefault(self.identifier, {})[self.plugin_state["ATTEMPTS"]] = sum(
                [[key]*value for key, value in htmlResponse[self.html_ids["Attempts"]].items()]
            , [])
        # Store the default competency extension at the time of the event, in the event
        # This way auto competency can be calculated dynamically
        e.pluginState.setdefault(self.identifier, {})[self.plugin_state["CURRENT DEFAULT"]] = \
            GENERIC_STATE_DATABASE.arb_int_state.get(self.plugin_state["DEFAULT"], DEFAULT_EXTENSION)
        return [Label("[COMPETENCY] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        questions = []
        track_attempts = GENERIC_STATE_DATABASE.arb_state.get(self.plugin_state["ATTEMPT TRACKING"], True)
        if track_attempts:
            # need this to convert the list of attempts as stored in the db to the structure understood by
            # AssassinDependentIntegerEntry
            def list_to_multiset(l: List[Any]) -> Dict[Any, int]:
                """Turns a list into a dict mapping values to how many times they appear in the list"""
                ms = dict()
                for item in l:
                    ms[item] = ms.get(item, 0) + 1
                return ms
            questions.append(
                Dependency(
                    dependentOn="CorePlugin_assassin_pseudonym",
                    htmlComponents=[
                        AssassinDependentIntegerEntry(
                            pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                            identifier=self.html_ids["Attempts"],
                            title="Add attempts/assists",
                            default=list_to_multiset(
                                e.pluginState.get(self.identifier, {}).get(self.plugin_state["ATTEMPTS"], {})
                            ),
                            global_default=1
                        )
                    ]
                )
            )

        mode = GENERIC_STATE_DATABASE.arb_state.setdefault(self.plugin_state["AUTO COMPETENCY"], "Auto")
        # Allow competency editing on event update even if full auto competency enabled.
        # TODO Make a selector that pre-filters to full players
        questions.append(Dependency(
            dependentOn="CorePlugin_assassin_pseudonym",
            htmlComponents=[
                AssassinDependentIntegerEntry(
                    pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                    identifier=self.html_ids["Competency"],
                    title="Manually extend competency?" if mode != "Manual" else "Extend competency?",
                    default=e.pluginState.get(self.identifier, {}).get(self.plugin_state["COMPETENCY"], {}),
                    global_default=GENERIC_STATE_DATABASE.arb_int_state.get(self.plugin_state["DEFAULT"],
                                                                            DEFAULT_EXTENSION)
                )
            ]
        ))
        return questions

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})[self.plugin_state["COMPETENCY"]] = htmlResponse[self.html_ids["Competency"]]
        if self.html_ids["Attempts"] in htmlResponse:
            # (see on_event_create)
            e.pluginState.setdefault(self.identifier, {})[self.plugin_state["ATTEMPTS"]] = sum(
                [[key] * value for key, value in htmlResponse[self.html_ids["Attempts"]].items()],
                []
            )
        return [Label("[COMPETENCY] Success!")]

    def on_page_request_generate(self) -> List[HTMLComponent]:
        now = get_now_dt()
        end = get_game_end()
        default = now if (end is None or now < end) else end  # to preserve the inco list at the end of game
        return [DatetimeEntry(
            identifier=self.html_ids["Datetime"],
            title="Enter date to calculate incos from",
            default=default
        )]

    def render_assassin_summary(self, assassin: Assassin) -> List[AttributePairTableRow]:
        pinfo = get_player_infos()[assassin.identifier]
        response = [("Competency status", str(pinfo.status))]
        if pinfo.status in [PlayerStatus.COMPETENT, PlayerStatus.INCOMPETENT]:
            datetime_str = datetime.datetime.strftime(pinfo.competency_deadline, DATETIME_FORMAT)
            response.append(("Competency deadline", datetime_str))
        return response

    def ask_show_inco_deadlines(self):
        return [NamedSmallTextbox(
            identifier=self.html_ids["Search"],
            title="Enter assassin names to search for (separate with commas for each searchable)"
        )]

    def answer_show_inco_deadlines(self, htmlResponse):
        search_terms = [t.strip() for t in htmlResponse[self.html_ids["Search"]].split(",")]

        player_infos = get_player_infos()
        deadlines = []
        for a in ASSASSINS_DATABASE.get_filtered(
                include=lambda x: any(t.lower() in x.identifier.lower() for t in search_terms)
        ):
            datetime_str = datetime.datetime.strftime(player_infos[a.identifier].competency_deadline, DATETIME_FORMAT)
            deadlines.append((a._secret_id,
                              a.real_name,
                              a.pseudonyms[0],
                              datetime_str,
                              str(player_infos[a.identifier].status)))
        deadlines.sort(key=lambda t: t[3])

        # our inquirer_cli rendering of Table uses the headings to determine column widths
        headings = ("ID",
                    "Real Name" + " "*20,
                    "Init. Pseudonym" + " "*20,
                    "Inco. Deadline" + " "*5,
                    "Comment" + " "*10)
        return [Table(deadlines, headings=headings)]

    def on_page_generate(self, htmlResponse) -> List[HTMLComponent]:
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda event: event.datetime)
        start_datetime: datetime.datetime = get_game_start()

        competency_manager = CompetencyManager(start_datetime)
        death_manager = DeathManager()
        limit = htmlResponse[self.html_ids["Datetime"]]
        for e in events:
            if e.datetime > limit:
                break
            competency_manager.add_event(e)
            death_manager.add_event(e)

        # dead incos != incos who are currently dead,
        # but rather players who died while inco.
        # note that `dead_incos` includes hidden assassins,
        # otherwise a player would disappear from the list of corpses when resurrected as part of the city watch
        dead_incos = competency_manager.inco_corpses
        alive_incos: List[Assassin] = [i for i in competency_manager.get_incos_at(limit)
                                       if not i.hidden
                                       and competency_manager.is_inco_at(i, limit)
                                       and not death_manager.is_dead(i)]

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

        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "inco.html"), "w+", encoding="utf-8") as F:
            F.write(
                INCOS_PAGE_TEMPLATE.format(
                    CONTENT="\n".join(tables),
                    YEAR=get_now_dt().year
                )
            )

        return [Label("[COMPETENCY] Success!")]
