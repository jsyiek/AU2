import datetime
import os
from html import escape
from typing import List, Dict, Tuple, Set

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import Assassin, Event
from AU2.html_components import HTMLComponent
from AU2.html_components.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.AssassinDependentSelector import AssassinDependentSelector
from AU2.html_components.AssassinDependentTextEntry import AssassinDependentTextEntry
from AU2.html_components.Dependency import Dependency
from AU2.html_components.InputWithDropDown import InputWithDropDown
from AU2.html_components.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
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

TRAITOR_TEMPLATE = 'bordercolor="#FF0000"'
MAFIA_TEMPLATE = 'bgcolor="{HEX}"'

PLAYER_ROW_TEMPLATE = "<tr {MAFIA} {TRAITOR}><td>{REAL_NAME}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{NOTES}</td></tr>"
PSEUDONYM_ROW_TEMPLATE = "<tr {MAFIA} {TRAITOR}><td>{PSEUDONYM}</td><td>{POINTS}</td><td>{PERMANENT_POINTS}</td><td>{OPEN_BOUNTIES}</td><td>{CLAIMED_BOUNTIES}</td><td>{TITLE}</td></tr>"


with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "may_week_mafia.html"), "r") as F:
    SCORE_PAGE_TEMPLATE = F.read()


CAPODECINA_MULTIPLIER = 1.25


class MafiaPlugin(AbstractPlugin):

    def __init__(self):
        super().__init__("MafiaPlugin")

        self.html_ids = {
            "Mafia": self.identifier + "_mafia",
            "Capodecina": self.identifier + "_capodecina",
            "Points": self.identifier + "_points",
            "Bounty": self.identifier + "_bounty",
            "Permanent Points": self.identifier + "_permanent_points"
        }

        self.plugin_state = {
            "MAFIA": "mafia",
            "CAPODECINA": "capodecina",
            "POINTS": "points",
            "BOUNTY": "bounties",
            "PERMANENT POINTS": "permanent_points"
        }

        self.exports = [
            Export(
                "create_mafia_score_page",
                "Generate page -> [MafiaPlugin] Scoring and player list",
                self.ask_generate_score_page,
                self.answer_generate_score_page
            )
        ]

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
        return [
            InputWithDropDown(
                self.html_ids["Mafia"],
                options=MAFIAS,
                title="Mafia",
                selected=a.plugin_state.get("MafiaPlugin", {}).get(self.plugin_state["MAFIA"], None)
            )
        ]

    def on_assassin_update(self, a: Assassin, htmlResponse) -> List[HTMLComponent]:
        mafia = htmlResponse[self.html_ids["Mafia"]]
        a.plugin_state.setdefault(self.identifier, {})[self.plugin_state["MAFIA"]] = mafia
        return [Label(f"[MAFIA] Mafia set to {mafia}!")]

    def on_event_request_create(self) -> List[HTMLComponent]:
        return [
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
                    AssassinDependentIntegerEntry(
                        identifier=self.html_ids["Points"],
                        title="Points: select players to manually adjust",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym"
                    ),
                    AssassinDependentIntegerEntry(
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

        return [Label("[MAFIA] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        capodecina = e.pluginState.get(self.identifier, {}).get(self.plugin_state["CAPODECINA"], None)
        points = e.pluginState.get(self.identifier, {}).get(self.plugin_state["POINTS"], None)
        permanent_points = e.pluginState.get(self.identifier, {}).get(self.plugin_state["PERMANENT POINTS"], None)
        bounty = e.pluginState.get(self.identifier, {}).get(self.plugin_state["BOUNTY"], None)
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentSelector(
                        identifier=self.html_ids["Capodecina"],
                        title="Set Capodecina (only need to do this once per day)",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        default=capodecina
                    ),
                    AssassinDependentIntegerEntry(
                        identifier=self.html_ids["Points"],
                        title="Points: select players to manually adjust",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        default=points
                    ),
                    AssassinDependentIntegerEntry(
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

        return [Label("[MAFIA] Success!")]

    def ask_generate_score_page(self) -> List[HTMLComponent]:
        return [Label("[MAFIA] Preparing...")]

    def answer_generate_score_page(self, _) \
            -> List[HTMLComponent]:
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
                point_gains[killer] += points[victim] * multiplier

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
                points[victim] /= 2

        wanted = {p: d for (p, d) in wanted.items() if d >= datetime.datetime.now()}

        """
        PLAYER_ROW_TEMPLATE = "<tr {MAFIA} {TRAITOR}><td>{REAL_NAME}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{NOTES}</td></tr>"
PSEUDONYM_ROW_TEMPLATE = "<tr {MAFIA} {TRAITOR}><td>{PSEUDONYM}</td><td>{POINTS}</td><td>{PERMANENT_POINTS}</td><td>{OPEN_BOUNTIES}</td><td>{CLAIMED_BOUNTIES}</td><td>{TITLE}</td></tr>"
        """

        player_rows: List[str] = []
        # tuple of total points and row
        pseudonym_rows: List[Tuple[float, str]] = []
        all_assassins = list(ASSASSINS_DATABASE.assassins.values())
        all_assassins.sort(key=lambda a: (a.college if a.college != "Casual" else "ZZZZZZZ", a.real_name))
        for a in all_assassins:
            mafia = a.plugin_state.get(self.identifier, {}).get(self.plugin_state["MAFIA"], "Casual")
            player_rows.append(
                PLAYER_ROW_TEMPLATE.format(
                    MAFIA=MAFIA_TEMPLATE.format(HEX=MAFIA_HEX[mafia]),
                    TRAITOR=TRAITOR_TEMPLATE if a.identifier in wanted else "",
                    REAL_NAME=escape(a.real_name),
                    ADDRESS=escape(a.address),
                    COLLEGE=escape(a.college),
                    WATER_STATUS=escape(a.water_status),
                    NOTES=escape(a.notes)
                )
            )

            pseudonym_row = PSEUDONYM_ROW_TEMPLATE.format(
                MAFIA=MAFIA_TEMPLATE.format(HEX=MAFIA_HEX[mafia]),
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

        pseudonym_rows.sort(key=lambda t: -t[0])

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
