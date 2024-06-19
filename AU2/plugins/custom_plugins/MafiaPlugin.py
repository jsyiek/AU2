import datetime
import os
import zlib
from html import escape
from typing import List, Dict, Tuple, Set, Optional

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import Assassin, Event
from AU2.html_components import HTMLComponent
from AU2.html_components.AssassinDependentFloatEntry import AssassinDependentFloatEntry
from AU2.html_components.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.AssassinDependentSelector import AssassinDependentSelector
from AU2.html_components.AssassinDependentTextEntry import AssassinDependentTextEntry
from AU2.html_components.Checkbox import Checkbox
from AU2.html_components.Dependency import Dependency
from AU2.html_components.InputWithDropDown import InputWithDropDown
from AU2.html_components.Label import Label
from AU2.html_components.LargeTextEntry import LargeTextEntry
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION

MAFIAS = [
    "The Crazy 88",
    "The Vengeance Pact",
    "The Family",
    "Casual"
]

MAFIA_HEX = {
    "The Crazy 88": "#FFA600",
    "The Vengeance Pact": "#B920DB",
    "The Family": "#BD0916",
    "Casual": "#BABABA"
}

LIGHT_MAFIA_HEX = {
    "The Crazy 88": "#FFD485",
    "The Vengeance Pact": "#F1B5FF",
    "The Family": "#DE9BA0",
    "Casual": "#BABABA"
}

TRAITOR_TEMPLATE = 'bordercolor="#FF0000"'
MAFIA_TEMPLATE = 'bgcolor="{HEX}"'

PLAYER_ROW_TEMPLATE = "<tr {MAFIA} {TRAITOR}><td>{REAL_NAME}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{NOTES}</td></tr>"
PSEUDONYM_ROW_TEMPLATE = "<tr {MAFIA} {TRAITOR}><td>{RANK}</td><td>{PSEUDONYM}</td><td>{POINTS}</td><td>{PERMANENT_POINTS}</td><td>{OPEN_BOUNTIES}</td><td>{CLAIMED_BOUNTIES}</td><td>{TITLE}</td></tr>"

CHAPTERS = {
    -1: "Prelude",
    0: "Chapter 1: L'Incontro (<i>The Meeting</i>)",
    1: "Chapter 2: La Scorta (<i>The Escort</i>)",
    2: "Chapter 3: Mercenaria (<i>Mercenaries</i>)",
    3: "Chapter 4: Lo Strappo (<i>Taken</i>)",
    4: "Chapter 5: Per Orgoglio (<i>For Pride</i>)",
    5: "Chapter 6: Quand E Troppo E Troppo (<i>What's Done is Done</i>)",
    6: "Chapter 7: Il Sicario (<i>The Duel</i>)",
    7: "Epilogue"
}

HEX_COLS = [
    '#B1AB8A', '#75C49C', '#7BA5A2', '#B0B477', '#B6CDBC',
    '#EC7DD2', '#B964EB', '#758FAC', '#EEABF2', '#6892B0',
    '#D9FBBF', '#D4A66A', '#8E7CE6', '#7CCC64', '#95B7F5',
    '#FF81EA', '#EB82D4', '#E89F6E', '#98A0CD', '#ACC6D0'
]

DEAD_COLS = [
    '#A9756C', '#A688BF', '#A34595'
]


DAY_EVENTS_TEMPLATE = """
<center><h3>{CHAPTER}</h3></center>
<br>
{EVENTS}
<br>
"""

EVENT_TEMPLATE = """
<p>{HEADLINE}</p>
{REPORTS}
"""

REPORT_TEMPLATE = """
<div style="margin-left:10%"><p><i>{TEXT}</i></p></div>
"""

PSEUDONYM_TEMPLATE = """<b style="color:{COLOR}">{PSEUDONYM}</b>"""

with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "may_week_mafia.html"), "r") as F:
    SCORE_PAGE_TEMPLATE = F.read()

with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "may_week_mafia_story.html"), "r") as F:
    THE_STORY_TEMPLATE = F.read()

CAPODECINA_MULTIPLIER = 1.25


@registered_plugin
class MafiaPlugin(AbstractPlugin):

    def __init__(self):
        super().__init__("MafiaPlugin")

        self.html_ids = {
            "Mafia": self.identifier + "_mafia",
            "Capodecina": self.identifier + "_capodecina",
            "Points": self.identifier + "_points",
            "Bounty": self.identifier + "_bounty",
            "Permanent Points": self.identifier + "_permanent_points",
            "Hidden": self.identifier + "_hidden",
            "Quote": self.identifier + "_quote"
        }

        self.plugin_state = {
            "MAFIA": "mafia",
            "CAPODECINA": "capodecina",
            "POINTS": "points",
            "BOUNTY": "bounties",
            "PERMANENT POINTS": "permanent_points",
            "HIDDEN": "hidden_event"
        }

        self.exports = [
            Export(
                "create_mafia_score_page",
                "Generate page -> Scoring and player list",
                self.ask_generate_score_page,
                self.answer_generate_score_page
            ),
            Export(
                "create_mafia_the_story",
                "Generate page -> The Story",
                self.ask_generate_the_story,
                self.answer_generate_the_story
            ),
            Export(
                "set_quote",
                "Set quote [MafiaPlugin]",
                self.ask_set_quote,
                self.answer_set_quote
            )
        ]

    def get_current_quote(self) -> Optional[str]:
        default = "No quote defined."
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda e: e.datetime)
        for e in events:
            if e.headline.startswith(f"[{self.identifier}] QUOTE: "):
                default = e.headline.replace(f"[{self.identifier}] QUOTE: ", "")
                break
        return default

    def ask_set_quote(self) -> List[HTMLComponent]:
        default = self.get_current_quote()
        return [
            LargeTextEntry(
                identifier=self.html_ids["Quote"],
                title="Enter quote",
                default=default,
            )
        ]

    def answer_set_quote(self, htmlResponse: Dict) -> List[HTMLComponent]:
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda e: e.datetime)
        quote = htmlResponse[self.html_ids["Quote"]]
        quote_event = None
        response = [Label("[MAFIA] Success!")]
        for e in events:
            if e.headline.startswith(f"[{self.identifier}] QUOTE: "):
                quote_event = e
                break
        else:
            quote_event = Event(
                assassins={},
                datetime=datetime.datetime(year=2010, month=1, day=1, hour=13),
                headline=f"[{self.identifier}] QUOTE: {quote}",
                reports={},
                kills=[],
                pluginState={self.identifier: {self.plugin_state["HIDDEN"]: True}}
            )
            EVENTS_DATABASE.add(quote_event)
            return response
        quote_event.headline = f"[{self.identifier}] QUOTE: {quote}"
        return response

    def on_assassin_request_create(self) -> List[HTMLComponent]:
        return [
            InputWithDropDown(
                self.html_ids["Mafia"],
                options=MAFIAS,
                title="Mafia"
            )
        ]

    def on_assassin_create(self, a: Assassin, htmlResponse) -> List[HTMLComponent]:
        mafia = htmlResponse[self.html_ids["Mafia"]]
        a.plugin_state.setdefault(self.identifier, {})[self.plugin_state["MAFIA"]] = mafia
        return [Label(f"[MAFIA] Mafia set to {mafia}!")]

    def on_assassin_request_update(self, a: Assassin) -> List[HTMLComponent]:
        hidden = a.plugin_state.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False)
        return [
            InputWithDropDown(
                self.html_ids["Mafia"],
                options=MAFIAS,
                title="Mafia",
                selected=a.plugin_state.get("MafiaPlugin", {}).get(self.plugin_state["MAFIA"], None)
            ),
            Checkbox(
                self.html_ids["Hidden"],
                title="Hidden: If 'Yes', not displayed on website",
                checked=hidden
            )
        ]

    def on_assassin_update(self, a: Assassin, htmlResponse) -> List[HTMLComponent]:
        mafia = htmlResponse[self.html_ids["Mafia"]]
        a.plugin_state.setdefault(self.identifier, {})[self.plugin_state["MAFIA"]] = mafia
        a.plugin_state[self.identifier][self.plugin_state["HIDDEN"]] = htmlResponse[self.html_ids["Hidden"]]
        return [Label(f"[MAFIA] Mafia set to {mafia}!")]

    def on_event_request_create(self) -> List[HTMLComponent]:
        return [
            Checkbox(self.html_ids["Hidden"], "Hidden: if 'Yes' then do not display on website", checked=False),
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    Label("NOTE: Capodecina only needs to be set once per day. Setting it multiple times in a day"
                          " is idempotent if done on the same person."),
                    AssassinDependentSelector(
                        identifier=self.html_ids["Capodecina"],
                        title="Set Capodecina (only need to do this once per day)",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym"
                    ),
                    AssassinDependentFloatEntry(
                        identifier=self.html_ids["Points"],
                        title="Points: select players to manually adjust",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym"
                    ),
                    AssassinDependentFloatEntry(
                        identifier=self.html_ids["Permanent Points"],
                        title="Permanent Points: select players to convert points to permanent",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                    ),
                    AssassinDependentTextEntry(
                        identifier=self.html_ids["Bounty"],
                        title="Bounty: select players to place a textual bounty on",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym"
                    )
                ]
            )
        ]

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})[self.plugin_state["CAPODECINA"]] = \
            htmlResponse[self.html_ids["Capodecina"]]
        e.pluginState[self.identifier][self.plugin_state["POINTS"]] = \
            htmlResponse[self.html_ids["Points"]]
        e.pluginState[self.identifier][self.plugin_state["BOUNTY"]] = htmlResponse[self.html_ids["Bounty"]]
        e.pluginState[self.identifier][self.plugin_state["PERMANENT POINTS"]] = htmlResponse[self.html_ids["Permanent Points"]]
        e.pluginState[self.identifier][self.plugin_state["HIDDEN"]] = htmlResponse[self.html_ids["Hidden"]]

        return [Label("[MAFIA] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        capodecina = e.pluginState.get(self.identifier, {}).get(self.plugin_state["CAPODECINA"], None)
        points = e.pluginState.get(self.identifier, {}).get(self.plugin_state["POINTS"], None)
        permanent_points = e.pluginState.get(self.identifier, {}).get(self.plugin_state["PERMANENT POINTS"], None)
        bounty = e.pluginState.get(self.identifier, {}).get(self.plugin_state["BOUNTY"], None)
        hidden = e.pluginState.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False)
        return [
            Checkbox(self.html_ids["Hidden"], "Hidden: if 'Yes' then do not display on website", checked=hidden),
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentSelector(
                        identifier=self.html_ids["Capodecina"],
                        title="Set Capodecina (only need to do this once per day)",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        default=capodecina
                    ),
                    AssassinDependentFloatEntry(
                        identifier=self.html_ids["Points"],
                        title="Points: select players to manually adjust",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        default=points
                    ),
                    AssassinDependentFloatEntry(
                        identifier=self.html_ids["Permanent Points"],
                        title="Permanent Points: select players to convert points to permanent",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        default=permanent_points
                    ),
                    AssassinDependentTextEntry(
                        identifier=self.html_ids["Bounty"],
                        title="Bounty: select players to place a textual bounty on",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        default=bounty
                    )
                ]
            )
        ]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})[self.plugin_state["CAPODECINA"]] = \
            htmlResponse[self.html_ids["Capodecina"]]
        e.pluginState[self.identifier][self.plugin_state["POINTS"]] = \
            htmlResponse[self.html_ids["Points"]]
        e.pluginState[self.identifier][self.plugin_state["BOUNTY"]] = htmlResponse[self.html_ids["Bounty"]]
        e.pluginState[self.identifier][self.plugin_state["PERMANENT POINTS"]] = htmlResponse[self.html_ids["Permanent Points"]]
        e.pluginState[self.identifier][self.plugin_state["HIDDEN"]] = htmlResponse[self.html_ids["Hidden"]]

        return [Label("[MAFIA] Success!")]

    def get_color(self, pseudonym: str, dead: bool=False) -> str:
        if "Vendetta" in pseudonym:
            return MAFIA_HEX["The Vengeance Pact"]
        elif "Don O'Hare" in pseudonym:
            return MAFIA_HEX["The Family"]
        elif "O-Ren Ishii" in pseudonym:
            return MAFIA_HEX["The Crazy 88"]

        ind = zlib.adler32(pseudonym.encode(encoding="utf-32"))
        if dead:
            return DEAD_COLS[ind % len(DEAD_COLS)]
        return HEX_COLS[ind % len(HEX_COLS)]

    def substitute_pseudonyms(self, string: str, main_pseudonym: str, assassin: Assassin, color: str) -> str:
        id_ = assassin._secret_id
        string = string.replace(f"[P{id_}]", PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=escape(main_pseudonym)))
        for i in range(len(assassin.pseudonyms)):
            string = string.replace(f"[P{id_}_{i}]", PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=escape(assassin.pseudonyms[i])))
        string = string.replace(f"[D{id_}]",
                                    " AKA ".join(PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=escape(p)) for p in assassin.pseudonyms))
        string = string.replace(f"[N{id_}]",
                                    PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=escape(assassin.real_name)))
        return string


    def ask_generate_the_story(self) -> List[HTMLComponent]:
        return [Label("[MAFIA] Preparing...")]

    def answer_generate_the_story(self, _) -> List[HTMLComponent]:
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda e: e.datetime)
        events_for_chapter = {}
        start_date: datetime.datetime = None
        for e in events:
            if e.headline.startswith("GAME START") and e.pluginState.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False):
                start_date = e.datetime.date()
                break
        else:
            return [Label(
                "[MAFIA] Could not determine game start. Create an event with headline GAME START and make it hidden.")]

        for e in events:
            # skip hidden events
            if e.pluginState.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False):
                continue

            days_since_start = (e.datetime.date() - start_date).days
            if days_since_start < 0:
                days_since_start = -1
            elif days_since_start > max(CHAPTERS):
                days_since_start = max(CHAPTERS)
            events_for_chapter.setdefault(days_since_start, [])

            is_dead: List[str] = []
            for (_, victim) in e.kills:
                is_dead.append(victim)

            headline = e.headline

            reports = {(playerID, pseudonymID): report for (playerID, pseudonymID, report) in e.reports}

            for (assassin, pseudonym_index) in e.assassins.items():
                assassin_model = ASSASSINS_DATABASE.get(assassin)
                pseudonym = assassin_model.pseudonyms[pseudonym_index]
                color = self.get_color(pseudonym, assassin in is_dead)
                headline = self.substitute_pseudonyms(headline, pseudonym, assassin_model, color)

                for (k, r) in reports.items():
                    reports[k] = self.substitute_pseudonyms(r, pseudonym, assassin_model, color)

            # For his May Week, Thomas O'Hare wants the reports to render *without* the pseudonym/real_name
            report_list = []
            for (_, r) in reports.items():
                report_list.append(
                    # not escaping r so we can have HTML in the reports
                    # I hope you know what you're doing, Thomas!
                    REPORT_TEMPLATE.format(TEXT=r)
                )
            report_text = "<br><br>".join(report_list)
            event_text = EVENT_TEMPLATE.format(HEADLINE=headline, REPORTS=report_text)
            events_for_chapter[days_since_start].append(event_text)

        all_chapters = []
        for (day, event_list) in events_for_chapter.items():
            all_event_text = "<br>".join(event_list)
            chapter_text = DAY_EVENTS_TEMPLATE.format(
                # again not escaping for same reason
                CHAPTER=CHAPTERS[day],
                EVENTS=all_event_text
            )
            all_chapters.append(chapter_text)

        all_chapter_text = """<hr style="width:30%;text-align:center"></hr>""".join(all_chapters)
        quote = self.get_current_quote()
        webpage_text = THE_STORY_TEMPLATE.format(QUOTE=quote, DAYS=all_chapter_text)

        path = os.path.join(WEBPAGE_WRITE_LOCATION, "head.html")

        with open(path, "w+") as F:
            F.write(webpage_text)

        return [Label("[MAFIA] Successfully generated the story!")]

    def ask_generate_score_page(self) -> List[HTMLComponent]:
        return [Label("[MAFIA] Preparing...")]

    def answer_generate_score_page(self, _) -> List[HTMLComponent]:
        """
        Takes in a list of events and calculates the points each player has and the earned bounties
        """
        events = list(EVENTS_DATABASE.events.values())

        points: Dict[str, float] = {}
        permanent_points: Dict[str, float] = {}
        open_bounties: Dict[str, List[str]] = {}
        earned_bounties: Dict[str, List[str]] = {}

        for a in ASSASSINS_DATABASE.assassins:
            assassin = ASSASSINS_DATABASE.get(a)
            if assassin.is_police:
                points[a] = 0
            else:
                points[a] = 1
            permanent_points[a] = 0
            earned_bounties[a] = []
            open_bounties[a] = []

        events.sort(key=lambda e: e.datetime)

        current_capos = []
        activity: Set[str] = set()
        wanted: Dict[str, datetime] = {}
        last_refresh = datetime.datetime(year=1000, month=1, day=1)

        warnings: List[Label] = []

        for e in events:

            # clear capodecina on new calendar day
            if e.datetime.day != last_refresh.day \
                    or e.datetime.month != last_refresh.month \
                    or e.datetime.year != last_refresh.year:
                current_capos = []
                last_refresh = e.datetime

            # update capodecina
            if e.pluginState.get(self.identifier, {}).get(self.plugin_state["CAPODECINA"], []):
                capodecina = e.pluginState[self.identifier][self.plugin_state["CAPODECINA"]]
                for c in capodecina:
                    current_capos.append(c)

            # calculate wanted
            if e.pluginState.get("WantedPlugin", {}):
                event_wanted = e.pluginState["WantedPlugin"]
                for playerID in event_wanted:
                    (duration, _, _) = event_wanted[playerID]
                    wanted[playerID] = e.datetime + datetime.timedelta(days=duration)

            # calculate player bounties
            if e.pluginState.get(self.identifier, {}).get(self.plugin_state["BOUNTY"], {}):
                bounties = e.pluginState[self.identifier][self.plugin_state["BOUNTY"]]
                for (playerID, bounty) in bounties.items():
                    open_bounties.setdefault(playerID, []).append(bounty)

            # compute permanent point conversion
            if e.pluginState.get(self.identifier, {}).get(self.plugin_state["PERMANENT POINTS"], {}):
                conversions = e.pluginState[self.identifier][self.plugin_state["PERMANENT POINTS"]]
                for (playerID, num_converted) in conversions.items():
                    convert = min(num_converted, points[playerID])
                    if convert < num_converted:
                        warnings.append(Label(title=f"[MAFIA] WARN: {e.identifier} has {playerID} converting "
                                                    f"{num_converted} into permanent, but they only have "
                                                    f"{points[playerID]} points!"))
                    points[playerID] -= convert
                    permanent_points[playerID] += convert

            # add assassins who participated in the event
            for a in e.assassins:
                activity.add(a)

            deaths = []
            point_gains = {}
            for (killer, victim) in e.kills:
                multiplier = 1

                if victim in current_capos:
                    multiplier *= 1.25
                if killer in current_capos:
                    multiplier *= 1.25
                if victim in wanted and wanted[victim] >= e.datetime:
                    multiplier *= 1.25
                    del wanted[victim]
                if open_bounties[victim]:
                    earned_bounties[killer] += open_bounties[victim]
                    open_bounties[victim] = []

                deaths.append(victim)
                point_gains.setdefault(killer, 0)
                point_gains[killer] += (1 + points[victim]/2) * multiplier

            # add BS points
            if e.pluginState.get(self.identifier, {}).get(self.plugin_state["POINTS"], {}):
                bs_points = e.pluginState[self.identifier][self.plugin_state["POINTS"]]
                for (playerID, bs) in bs_points.items():
                    point_gains.setdefault(playerID, 0)
                    point_gains[playerID] += bs

            # must credit killers first
            # kills all happen simultaneously
            # so must buffer the point gains before applying
            # (e.g. in the case of circular kills such as if
            # Don O'Hare kills Vendetta kills Don O'Hare)
            for (killer, gain) in point_gains.items():
                points[killer] += gain

            for victim in deaths:
                points[victim] = max(points[victim]/2, 1)

        wanted = {p: d for (p, d) in wanted.items() if d >= datetime.datetime.now()}

        player_rows: List[str] = []
        # tuple of total points and row
        pseudonym_rows: List[Tuple[float, str]] = []
        all_assassins = list(a for a in ASSASSINS_DATABASE.assassins.values() if not a.plugin_state.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False))
        all_assassins.sort(key=lambda a: (a.college if a.college != "Casual" else "ZZZZZZZ", a.real_name))
        for a in all_assassins:
            mafia = a.plugin_state.get(self.identifier, {}).get(self.plugin_state["MAFIA"], "Casual")
            player_rows.append(
                PLAYER_ROW_TEMPLATE.format(
                    MAFIA=MAFIA_TEMPLATE.format(HEX=LIGHT_MAFIA_HEX[mafia]),
                    TRAITOR=TRAITOR_TEMPLATE if a.identifier in wanted else "",
                    REAL_NAME=escape(a.real_name),
                    ADDRESS=escape(a.address),
                    COLLEGE=escape(a.college),
                    WATER_STATUS=escape(a.water_status),
                    NOTES=escape(a.notes)
                )
            )

        assassins_with_points = [(a, points[a.identifier] + permanent_points[a.identifier]) for a in all_assassins]
        assassins_with_points.sort(key=lambda t: (-t[1], t[0]._secret_id))

        for (i, (a, p)) in enumerate(assassins_with_points):
            mafia = a.plugin_state.get(self.identifier, {}).get(self.plugin_state["MAFIA"], "Casual")
            i = i + 1
            pseudonym_row = PSEUDONYM_ROW_TEMPLATE.format(
                RANK=str(i),
                MAFIA=MAFIA_TEMPLATE.format(HEX=LIGHT_MAFIA_HEX[mafia]),
                TRAITOR=TRAITOR_TEMPLATE if a.identifier in wanted else "",
                PSEUDONYM=escape(a.all_pseudonyms()),
                POINTS=escape(str(round(points[a.identifier] + permanent_points[a.identifier], 2))),
                PERMANENT_POINTS=escape(str(round(permanent_points[a.identifier], 2))),
                OPEN_BOUNTIES=escape(", ".join(open_bounties[a.identifier])),
                CLAIMED_BOUNTIES=escape(", ".join(earned_bounties[a.identifier])),
                TITLE="Capodecina" if a.identifier in current_capos else ""
            )
            total_points = round(points[a.identifier] + permanent_points[a.identifier], 2)
            pseudonym_rows.append((total_points, pseudonym_row))

        all_pseud_rows = [p for (_, p) in pseudonym_rows]

        pseudonym_text = "\n".join(all_pseud_rows)
        player_text = "\n".join(player_rows)

        webpage = SCORE_PAGE_TEMPLATE.format(
            PSEUDONYM_ROWS=pseudonym_text,
            PLAYER_ROWS=player_text
        )

        path = os.path.join(WEBPAGE_WRITE_LOCATION, "openseason.html")
        with open(path, "w+") as F:
            F.write(webpage)

        return warnings + [Label("[MAFIA] Success!")]
