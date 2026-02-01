from collections import defaultdict
import dataclasses
import functools
from typing import DefaultDict, Dict, List, Optional, Sequence, Set

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.DependentComponents.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.DependentComponents.AssassinDependentTransferEntry import AssassinDependentTransferEntry
from AU2.html_components.DependentComponents.KillDependentSelector import KillDependentSelector
from AU2.html_components.DependentComponents.AssassinDependentInputWithDropdown import AssassinDependentInputWithDropDown
from AU2.html_components.MetaComponents.Dependency import Dependency
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.IntegerEntry import IntegerEntry
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.LargeTextEntry import LargeTextEntry
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown
from AU2.html_components.SimpleComponents.Table import Table
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport, Export, AttributePairTableRow
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.date_utils import get_now_dt
from AU2.plugins.util.render_utils import Chapter, generate_news_pages, get_color, Manager


HEX_COLS = [
    '#00A6A3', '#26CCC8', '#008B8A', '#B69C1F',
    '#D1B135', '#5B836E', '#7A9E83', '#00822b',
    '#00A563', '#FFA44D', '#CC6C1E', '#37b717',
    '#27B91E', '#1F9E1A', '#3DC74E', '#00c6c3',
    '#b7a020', '#637777', '#f28110'
]

CREW_COLOR_TEMPLATE = 'style="background-color:{HEX}"'
TEAM_ENTRY_TEMPLATE = "<td {CREW_COLOR}>{TEAM}</td>"
TEAM_HDR_TEMPLATE = "<th>{TEAM_STR}</th>"
PLAYER_ROW_TEMPLATE = "<tr><td>{REAL_NAME}</td><td>{PLAYER_TYPE}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{NOTES}</td></tr>"
PSEUDONYM_ROW_TEMPLATE = ("<tr><td {CREW_COLOR}>{PSEUDONYM}</td>"
                         "<td {CREW_COLOR}>{POINTS}</td>"
                         "<td {CREW_COLOR}>{MULTIPLIER}</td>"
                         "{TEAM_ENTRY}</tr>")

MAYWEEK_PLAYERS_TEMPLATE_PATH = ROOT_DIR / "plugins" / "custom_plugins" / "html_templates" / "may_week_utils_players.html"
with open(MAYWEEK_PLAYERS_TEMPLATE_PATH, "r", encoding="utf-8", errors="ignore") as F:
    MAYWEEK_PLAYERS_TEMPLATE = F.read()

MAYWEEK_NEWS_TEMPLATE_PATH = ROOT_DIR / "plugins" / "custom_plugins" / "html_templates" / "may_week_utils_news.html"
with open(MAYWEEK_NEWS_TEMPLATE_PATH, "r", encoding="utf-8", errors="ignore") as F:
    MAYWEEK_NEWS_TEMPLATE = F.read()

@dataclasses.dataclass
class ScoringParameter:
    name: str
    default_value: int
    description: str

    def identifier(self) -> str:
        return f"may_week_scoring_{self.name}"

@registered_plugin
class MayWeekUtilitiesPlugin(AbstractPlugin):
    """
    This is a generic May Week plugin to support common May Week game features.

    **Casual players**: This is a cosmetic change; there is no City Watch in May Week,
              so this plugin reinterprets members of the city watch as 'casual' players.

    **Teams**: Any number of players can be part of a team. Kills can be made as part
               of a team and points will be shared across all players (and bonus points
               added)

    **Multipliers**: Players can earn point multipliers (e.g., Capodecina, compasses)
                     at the umpire's discretion. These award bonus points for kills.

    **Scoring**: May Week scoring is bespoke and is a fixed function of the above.
    """
    def __init__(self):
        super().__init__(type(self).__name__)

        self.html_ids = {
            "Team Names": self.identifier + "_team_names",
            "Enable Teams?": self.identifier + "_enable_teams",
            "Share Multipliers?": self.identifier + "_share_multipliers",
            "Assassins": self.identifier + "_assassins",
            "Team ID": self.identifier + "_team_id",
            "Team Changes": self.identifier + "_team_changes",
            "Multiplier Transfer": self.identifier + "_multiplier_transfer",
            "Kills as Team": self.identifier + "_kills_as_team",
            "BS Points": self.identifier + "_bs_points",
            "Event Secret ID": self.identifier + "_event_secret_id"
        }

        self.plugin_state = {
            "Team Names": "team_names",
            "Enable Teams?": "enable_teams",
            "Share Multipliers?": "share_multipliers",
            "Team Members": "team_members",
            "Team Changes": "team_changes",
            "Multiplier Transfers": "multiplier_transfers",
            "Kills as Team": "kills_as_team",
            "BS Points": "bs_points",
        }

        self.ps_defaults = {
            "Team Names": ["Team 1", "Team 2", "Team 3"],
            "Share Multipliers?": False
        }

        self.cosmetics = [
            "Multiplier",
            "Teams",
        ]
        self.html_ids.update({k: self.identifier + "_" + k.lower() for k in self.cosmetics})
        self.plugin_state.update({k: k.lower() for k in self.cosmetics})

        self.scoring_parameters = [
            ScoringParameter(
                name="starting_score_casual",
                default_value=0,
                description="Sc = starting score of casual players"
            ),
            ScoringParameter(
                name="starting_score_full",
                default_value=10,
                description="Sf = starting score of full players"
            ),
            ScoringParameter(
                name="death_penalty_pct",
                default_value=35,
                description="d = % of points lost by a player when they die"
            ),
            ScoringParameter(
                name="death_penalty_fixed",
                default_value=1,
                description="D = Fixed number of points lost by player when they die"
            ),
            ScoringParameter(
                name="kill_bonus_pct",
                default_value=135,
                description="b = % of victim's points gained by the killer"
            ),
            ScoringParameter(
                name="kill_bonus_fixed",
                default_value=1,
                description="B = Fixed points awarded for each kill"
            ),
            ScoringParameter(
                name="team_bonus_pct",
                default_value=115,
                description="t = % bonus points awarded overall when the kill is made with a team"
            ),
            ScoringParameter(
                name="team_bonus_fixed",
                default_value=1,
                description="T = Fixed points awarded when kills are made with a team"
            ),
            ScoringParameter(
                name="multiplier_bonus_pct",
                default_value=125,
                description="m = % bonus points obtained for a player when they kill with a multiplier"
            ),
            ScoringParameter(
                name="multiplier_bonus_fixed",
                default_value=1,
                description="M = Fixed points awarded when kills are made with a multiplier"
            )
        ]
        self.html_ids.update({param.name: self.identifier + "_" + param.name.lower() for param in self.scoring_parameters})
        self.plugin_state.update({param.name: param.identifier() for param in self.scoring_parameters})

        for p in self.scoring_parameters:
            self.gsdb_set(p.name, p.default_value)

        self.printable_gain_formula = "Points gained from kills: ((V*b + B)*t + T)*m + M"
        self.printable_loss_formula = "Points lost from death: -V*d - D"

        self.exports = [
            Export(
                "may_week_crews_summary",
                "May Week -> Teams Summary",
                self.ask_teams_summary,
                self.answer_teams_summary
            )
        ]

        self.config_exports = [
            ConfigExport(
                identifier="may_week_enable_teams",
                display_name="May Week -> Enable/disable Teams",
                ask=self.ask_enable_teams,
                answer=self.answer_enable_teams
            ),
            ConfigExport(
                identifier="may_week_set_team_names",
                display_name="May Week -> Rename Teams",
                ask=self.ask_name_teams,
                answer=self.answer_name_teams
            ),
            ConfigExport(
                identifier="may_week_enable_multiplier_team_sharing",
                display_name="May Week -> Enable/disable multiplier team sharing",
                ask=self.ask_enable_multiplier_team_sharing,
                answer=self.answer_enable_multiplier_team_sharing
            ),
            ConfigExport(
                identifier="may_week_cosmetics",
                display_name="May Week -> Tweak Cosmetics",
                ask=self.ask_tweak_cosmetics,
                answer=self.answer_tweak_cosmetics
            ),
            ConfigExport(
                identifier="may_week_scoring_parameters",
                display_name="May Week -> Set Scoring Parameters",
                ask=self.ask_set_scoring_params,
                answer=self.answer_set_scoring_params
            )
        ]

        class TeamManager:
            """Helps keep track of teams"""
            def __init__(self):
                self.member_to_team: DefaultDict[str, Optional[int]] = defaultdict(lambda: None)

            def add_event(TeamManager_self, e: Event):
                nonlocal self
                team_memb_changes = self.eps_get(e, "Team Changes", {})
                TeamManager_self.member_to_team.update(team_memb_changes)
                TeamManager_self.team_to_member_map.cache_clear()

            def process_events_until(self, before_event: int = float("Inf")) -> "TeamManager":
                for e in EVENTS_DATABASE.events.values():
                    if int(e._Event__secret_id) >= before_event:
                        continue
                    self.add_event(e)
                return self

            @functools.cache
            def team_to_member_map(self) -> DefaultDict[Optional[int], Set[str]]:
                """Produces the 'inverse' of member_to_team, i.e. a map from teams to sets of assassin identifiers"""
                memb_map = defaultdict(lambda: set())
                for a, c in self.member_to_team.items():
                    if c is not None:  # stop individuals being grouped into a team
                        memb_map[c].add(a)
                return memb_map
        self.TeamManager = TeamManager

    def gsdb_get(self, plugin_state_id, default):
        return GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get(self.plugin_state[plugin_state_id], default)

    def gsdb_set(self, plugin_state_id, data):
        GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {})[self.plugin_state[plugin_state_id]] = data

    def eps_get(self, e: Event, plugin_state_id, default):
        return e.pluginState.get(self.identifier, {}).get(self.plugin_state[plugin_state_id], default)

    def eps_set(self, e: Event, plugin_state_id, data):
        e.pluginState.setdefault(self.identifier, {})[self.plugin_state[plugin_state_id]] = data


    def ask_enable_teams(self):
        return [Checkbox(
            title="Enable teams?",
            identifier=self.html_ids["Enable Teams?"],
            checked=self.gsdb_get("Enable Teams?", False)
        )]

    def answer_enable_teams(self, html_response):
        enabled = html_response[self.html_ids["Enable Teams?"]]
        self.gsdb_set("Enable Teams?", enabled)
        return [
            Label("Teams are now: " + "enabled" if enabled else "disabled")
        ]

    def ask_enable_multiplier_team_sharing(self):
        return [Checkbox(
            title="Should multipliers be shared within teams?",
            identifier=self.html_ids["Share Multipliers?"],
            checked=self.gsdb_get("Share Multipliers?", self.ps_defaults["Share Multipliers?"])
        )]

    def answer_enable_multiplier_team_sharing(self, html_response):
        enabled = html_response[self.html_ids["Share Multipliers?"]]
        self.gsdb_set("Share Multipliers?", enabled)
        return [
            Label("Team multiplier sharing is now: " + "enabled" if enabled else "disabled")
        ]

    def ask_name_teams(self):
        existing_ranks: List[str] = self.gsdb_get("Team Names", self.ps_defaults["Team Names"])
        default_text = "# Enter team names each on a new line.\n# Lines starting with hashtags will be ignored.\n"
        return [
            LargeTextEntry(
                title="Rename teams",
                identifier=self.html_ids["Team Names"],
                default=default_text + "\n".join(existing_ranks)
            )
        ]

    def answer_name_teams(self, html_response):
        team_list = list(
            filter(lambda t: t.strip() and not t.strip().startswith("#") ,
                html_response[self.html_ids["Team Names"]].split("\n")))
        if not team_list:
            return [Label("ERROR! You must specify at least one team. (They can't start with #.)")]
        self.gsdb_set("Team Names", team_list)
        return [Label(f"SUCCESS! New teams: {team_list}")]

    def ask_tweak_cosmetics(self):
        return [
            DefaultNamedSmallTextbox(
                identifier=self.html_ids[cosmetic],
                title=f"What do you want to call {cosmetic}?",
                default=self.gsdb_get(cosmetic, cosmetic)
            ) for cosmetic in self.cosmetics
        ]

    def answer_tweak_cosmetics(self, html_response):
        for cosmetic in self.cosmetics:
            self.gsdb_set(cosmetic, html_response[self.html_ids[cosmetic]])

        return [
            Label(f"{cosmetic} will now be displayed as {html_response[self.html_ids[cosmetic]]}! (in generated pages)")
            for cosmetic in self.cosmetics
        ]

    def ask_set_scoring_params(self):
        return [
            Label("Set scoring parameters for the following formulae:"),
            Label(self.printable_gain_formula),
            Label(self.printable_loss_formula),
            *(IntegerEntry(
                title=param.description,
                default=self.gsdb_get(param.name, param.default_value),
                identifier=self.html_ids[param.name]
            ) for param in self.scoring_parameters)
        ]

    def answer_set_scoring_params(self, html_response):
        for param in self.scoring_parameters:
            self.gsdb_set(param.name, html_response[self.html_ids[param.name]])

        return [
            Label(title=f"Parameter {param.name} set to {html_response[self.html_ids[param.name]]}")
            for param in self.scoring_parameters
        ]

    def ask_teams_summary(self) -> List[HTMLComponent]:
        return [
            # TODO: PR #143 might be able to solve this
            Label(f"Note: due to technical limitations, {self.identifier} processes events in the order in which they "
                  f"were added, not in order of the datetimes assigned to each event."),
            InputWithDropDown(identifier=self.html_ids["Event Secret ID"],
                              title="Select the event AFTER which to view team status",
                              options=[
                                  (f"({e._Event__secret_id}) "
                                   f"[{e.datetime.strftime('%Y-%m-%d %H:%M %p')}] {e.headline[0:25].rstrip()}",
                                   e._Event__secret_id)
                                  for e in reversed(EVENTS_DATABASE.events.values())
                              ])
        ]

    def answer_teams_summary(self, htmlResponse) -> List[HTMLComponent]:
        teams_str = self.get_cosmetic_name("Teams").capitalize()
        multiplier_str = self.get_cosmetic_name("Multiplier").capitalize()
        team_manager = self.TeamManager().process_events_until(before_event=int(
            htmlResponse[self.html_ids["Event Secret ID"]]) + 1
        )
        team_to_members = team_manager.team_to_member_map()
        team_names = self.gsdb_get("Team Names", self.ps_defaults["Team Names"])
        multiplier_owners = self.get_multiplier_owners()
        rows = []
        for team_id, team_name in sorted(enumerate(team_names), key=lambda x: x[1]):
            members = team_to_members[team_id]
            for member in members:
                rows.append([team_name, member, "Y" if member in multiplier_owners else ""])
                # "merge" rows in the team name
                team_name = ""
        return [
            Table(
                rows or [[]],
                headings=[teams_str.ljust(50), "Members".ljust(50), multiplier_str]
            )
        ]

    def render_assassin_summary(self, assassin: Assassin) -> List[AttributePairTableRow]:
        team_str = self.get_cosmetic_name("Teams").capitalize()
        multiplier_str = self.get_cosmetic_name("Multiplier").lower()
        teams_enabled = self.gsdb_get("Enable Teams?", False)
        team_names = self.gsdb_get("Team Names", self.ps_defaults["Team Names"])
        team_manager = self.TeamManager()
        scores = self.calculate_scores(team_manager=team_manager)
        multiplier_owners = self.get_multiplier_owners()
        multiplier_beneficiaries = self.get_multiplier_beneficiaries(multiplier_owners, team_manager)

        team = team_manager.member_to_team[assassin.identifier]
        team_name = team_names[team] if team is not None else "(Individual)"

        return [
            ("Score", scores[assassin.identifier]),
            # will render as plural, but eh
            *((team_str, team_name) for _ in range(teams_enabled)),
            (f"Has {multiplier_str}", "Y" if assassin.identifier in multiplier_owners else "N"),
            (f"Benefits from {multiplier_str}", "Y" if assassin.identifier in multiplier_beneficiaries else "N")
        ]

    def render_event_summary(self, event: Event) -> List[AttributePairTableRow]:
        response = []

        snapshot = lambda a: f"{a.real_name} ({a._secret_id})" # TODO: move to common library location

        if self.gsdb_get("Enable Teams?", False):
            team_names = self.gsdb_get("Team Names", self.ps_defaults["Team Names"])
            team_str = self.get_cosmetic_name("Teams").capitalize()
            for i, (a_id, t_id) in enumerate(self.eps_get(event, "Team Changes", {}).items()):
                a = ASSASSINS_DATABASE.get(a_id)
                change_str = f"{snapshot(a)} " + (
                    f"joins {team_names[t_id]}" if t_id is not None
                    else "goes it alone"
                )
                response.append((f"{team_str} Change {i+1}", change_str))
            for i, (killer_id, victim_id) in enumerate(self.eps_get(event, "Kills as Team", [])):
                killer = ASSASSINS_DATABASE.get(killer_id)
                victim = ASSASSINS_DATABASE.get(victim_id)
                response.append((f"{team_str} Kill {i+1} ", f"{snapshot(killer)} kills {snapshot(victim)}"))

        multiplier_str = self.get_cosmetic_name("Multiplier").capitalize()
        for i, (old_owner, receiver) in enumerate(self.eps_get(event, "Multiplier Transfers", [])):
            a1 = snapshot(ASSASSINS_DATABASE.get(old_owner)) if old_owner is not None else "None"
            a2 = snapshot(ASSASSINS_DATABASE.get(receiver)) if receiver is not None else "None"
            response.append((f"{multiplier_str} Transfer {i+1}", f"{a1} -> {a2}"))

        for i, (a_id, points) in enumerate(self.eps_get(event, "BS Points", {}).items()):
            a = ASSASSINS_DATABASE.get(a_id)
            response.append((f"BS Points for {snapshot(a)}", f"{points}"))

        return response

    def get_cosmetic_name(self, name: str) -> str:
        return self.gsdb_get(name, name.lower())

    def get_multiplier_owners(self, before_event: int = float("inf")) -> List[str]:
        owners = set()
        for event in EVENTS_DATABASE.events.values():
            if int(event._Event__secret_id) >= before_event:
                continue
            key = self.plugin_state["Multiplier Transfers"]
            for (loser, gainer) in event.pluginState.get(self.identifier, {}).get(key, []):
                if loser is not None and loser in owners:
                    owners.remove(loser)
                if gainer is not None:
                    owners.add(gainer)
        return list(owners)

    def get_multiplier_beneficiaries(self, multiplier_owners: List[str], team_manager) -> List[str]:
        teams_enabled = self.gsdb_get("Enable Teams?", False)
        if teams_enabled:
            member_to_team = team_manager.member_to_team
            team_to_members = team_manager.team_to_member_map()

        multiplier_beneficiaries = multiplier_owners
        # gives all players on a team with a holder of a multiplier,
        # for the case of shared multipliers
        sharing_multipliers = teams_enabled and self.gsdb_get("Share Multipliers?", self.ps_defaults["Share Multipliers?"])
        if sharing_multipliers:
            multiplier_beneficiaries = [
                member for owner in multiplier_owners for member in team_to_members[member_to_team[owner]]
            ]
        return multiplier_beneficiaries

    def on_event_request_create(self) -> List[HTMLComponent]:
        multiplier_str = self.get_cosmetic_name("Multiplier").lower()
        teams_str = self.get_cosmetic_name("Teams").lower()
        teams_enabled = self.gsdb_get("Enable Teams?", False)
        team_names = self.gsdb_get("Team Names", self.ps_defaults["Team Names"])
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentIntegerEntry(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["BS Points"],
                        title="[MAY WEEK] Want to award any BS points?",
                    ),
                    Label(f"[MAY WEEK] WARNING! Changing this will not play nicely if the {multiplier_str} has already "
                          "transferred again after this!"),
                    AssassinDependentTransferEntry(
                        assassins_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Multiplier Transfer"],
                        owners=self.get_multiplier_owners(),
                        title=f"[MAY WEEK] Any {multiplier_str} transfers? (None -> A adds a new {multiplier_str}, A -> None deletes it)"
                    ),

                    *(AssassinDependentInputWithDropDown(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Team Changes"],
                        title=f"[MAY WEEK] Select players who changed {teams_str} "
                              f"(note: this will be considered to have happened *before* any kills)",
                        options=[("(Individual)", None), *((name, i) for i, name in enumerate(team_names))],
                    ) for _ in range(teams_enabled)),
                    *(Dependency(
                        dependentOn="CorePlugin_kills",
                        htmlComponents=[
                            KillDependentSelector(
                                identifier=self.html_ids["Kills as Team"],
                                kills_identifier="CorePlugin_kills",
                                title=f"[MAY WEEK] Which kills were made in a {teams_str}, for the purposes of scoring?",
                            )
                        ]
                    ) for _ in range(teams_enabled))
                ]
            ),
        ]

    def on_event_create(self, e: Event, html_response) -> List[HTMLComponent]:
        self.eps_set(e, "Multiplier Transfers", html_response[self.html_ids["Multiplier Transfer"]])
        self.eps_set(e, "BS Points",  html_response[self.html_ids["BS Points"]])
        if self.html_ids["Kills as Team"] in html_response:
            self.eps_set(e, "Kills as Team", html_response[self.html_ids["Kills as Team"]])
        if self.html_ids["Team Changes"] in html_response:
            self.eps_set(e, "Team Changes", html_response[self.html_ids["Team Changes"]])
        return [Label("[MAY WEEK] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        multiplier_str = self.get_cosmetic_name("Multiplier").lower()
        teams_str = self.get_cosmetic_name("Teams").lower()
        teams_enabled = self.gsdb_get("Enable Teams?", False)
        team_names = self.gsdb_get("Team Names", self.ps_defaults["Team Names"])
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentIntegerEntry(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["BS Points"],
                        title="Want to award any BS points?",
                        default=self.eps_get(e, "BS Points", {})
                    ),
                    Label(f"[MAY WEEK] WARNING! Changing this will not play nicely if the {multiplier_str} has already "
                          "transferred again after this!"),
                    AssassinDependentTransferEntry(
                        assassins_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Multiplier Transfer"],
                        owners=self.get_multiplier_owners(before_event=int(e._Event__secret_id)),
                        title=f"[MAY WEEK] Any {multiplier_str} transfers?",
                        default=self.eps_get(e, "Multiplier Transfers", [])
                    ),
                    *(AssassinDependentInputWithDropDown(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Team Changes"],
                        title=f"[MAY WEEK] Select players who changed {teams_str}",
                        options=[("(Individual)", None), *((name, i) for i, name in enumerate(team_names))],
                        default=self.eps_get(e, "Team Changes", {})
                    ) for _ in range(teams_enabled)),
                    *(Dependency(
                        dependentOn="CorePlugin_kills",
                        htmlComponents=[
                            KillDependentSelector(
                                identifier=self.html_ids["Kills as Team"],
                                kills_identifier="CorePlugin_kills",
                                title=f"[MAY WEEK] Which kills were made in a {teams_str}, for the purposes of scoring?",
                                default=self.eps_get(e, "Kills as Team", [])
                            )
                        ]
                    ) for _ in range(teams_enabled))
                ]
            ),
        ]

    def on_event_update(self, e: Event, html_response) -> List[HTMLComponent]:
        self.eps_set(e, "Multiplier Transfers", html_response[self.html_ids["Multiplier Transfer"]])
        self.eps_set(e, "BS Points",  html_response[self.html_ids["BS Points"]])
        if self.html_ids["Kills as Team"] in html_response:
            self.eps_set(e, "Kills as Team", html_response[self.html_ids["Kills as Team"]])
        if self.html_ids["Team Changes"] in html_response:
            self.eps_set(e, "Team Changes", html_response[self.html_ids["Team Changes"]])
        return [Label("[MAY WEEK] Success!")]

    def calculate_scores(self, before_event: int = float("inf"), team_manager = None) -> Dict[str, float]:
        d = self.gsdb_get("death_penalty_pct", 0) / 100
        D = self.gsdb_get("death_penalty_fixed", 0)
        b = self.gsdb_get("kill_bonus_pct", 0) / 100
        B = self.gsdb_get("kill_bonus_fixed", 0)
        t = self.gsdb_get("team_bonus_pct", 0) / 100
        T = self.gsdb_get("team_bonus_fixed", 0)
        m = self.gsdb_get("multiplier_bonus_pct", 0) / 100
        M = self.gsdb_get("multiplier_bonus_fixed", 0)
        Sc = self.gsdb_get("starting_score_casual", 0)
        Sf = self.gsdb_get("starting_score_full", 0)

        # passing a team manager allows us to extract team information after this function runs
        team_manager = team_manager or self.TeamManager()

        scores: Dict[str, float] = {a.identifier: Sf if not a.is_city_watch else Sc for a in ASSASSINS_DATABASE.get_filtered(
            include_hidden = lambda _: True  # probably not necessary in May Week (since no resurrection as city watch),
                                             # but just in case...
        )}
        multiplier_owners = set()
        teams_enabled = self.gsdb_get("Enable Teams?", False)
        team_multiplier_sharing_enabled = teams_enabled and self.gsdb_get("Share Multipliers?", self.ps_defaults["Share Multipliers?"])

        # unfortunately events have to processed in order of secret id (i.e. in the order they were created)
        # so that the multiplier transfer interface in Event -> Create / Event -> Update  works correctly...
        for e in EVENTS_DATABASE.events.values():
            if int(e._Event__secret_id) > before_event:
                continue
            kills_made_as_team = self.eps_get(e, "Kills as Team", [])
            bs_points = self.eps_get(e, "BS Points", {}).items()

            # update team memberships
            team_manager.add_event(e)
            member_to_team = team_manager.member_to_team
            team_to_members = team_manager.team_to_member_map()

            # updates happen atomically, so we calculate them as a batch and then add them back in
            point_deltas = {player: bs_allotment for (player, bs_allotment) in bs_points}

            for (killer, victim) in e.kills:
                is_as_team = teams_enabled and (killer, victim) in kills_made_as_team
                is_with_multiplier = killer in multiplier_owners
                if team_multiplier_sharing_enabled and not is_with_multiplier:
                    # check whether the killer is in the same team as someone with a multiplier
                    is_with_multiplier = any(memb in multiplier_owners for memb in team_to_members[member_to_team[killer]])

                # apply team and multiplier bonuses (% and fixed) iff they apply
                # (side note: maybe calling the items that grant bonuses multipliers is a little confusing in this
                #  context, since they are neither the only ways to get multiplicative bonuses (teams do that)
                #  nor do they only grant multiplicative bonuses)
                t_now = t if is_as_team else 1
                T_now = T if is_as_team else 0
                m_now = m if is_with_multiplier else 1
                M_now = M if is_with_multiplier else 0

                point_deltas[killer] = point_deltas.get(killer, 0) + ((scores[victim]*b + B)*t_now + T_now)*m_now + M_now
                point_deltas[victim] = point_deltas.get(victim, 0) - scores[victim]*d - D

            # resolve deltas once all worked out
            for player in point_deltas:
                # use max or else you can LOSE points by killing someone!
                # (specifically, if killing a player with negative points would lose you points)
                scores[player] = max(0, scores[player] + point_deltas[player])

            # work out any multiplier transfers
            for (loser, gainer) in e.pluginState.get(self.identifier, {}).get(self.plugin_state["Multiplier Transfers"], []):
                if loser is not None and loser in multiplier_owners:
                    multiplier_owners.remove(loser)
                if gainer is not None:
                    multiplier_owners.add(gainer)

        return scores

    def on_page_generate(self, htmlResponse) -> List[HTMLComponent]:
        """
        Generates player info page and may week news page.

        The player info page displays two lists, one giving player pseudonyms, scores, teams (if applicable) and
        multipliers, the other giving the real names and other targeting information for all the players.

        The may week news page collates all the events onto a single page (rather than paginating like
        PageGeneratorPlugin) and applies May Week name colouring (i.e. crews share a colour, don't colour city watch
        (casual players) differently, don't colour dead players differently outside the event in which they died, don't
        colourincos).
        """

        # player info page
        team_manager = self.TeamManager()
        scores = self.calculate_scores(team_manager=team_manager)
        multiplier_owners = set(self.get_multiplier_owners())
        teams_enabled = self.gsdb_get("Enable Teams?", False)
        member_to_team = team_manager.member_to_team
        team_to_members = team_manager.team_to_member_map()
        team_names = self.gsdb_get("Team Names", self.ps_defaults["Team Names"])
        multiplier_beneficiaries = self.get_multiplier_beneficiaries(multiplier_owners, team_manager)

        team_to_hex_col = {}
        for (i, team) in enumerate(team_to_members):
            team_to_hex_col[team] = HEX_COLS[i % len(HEX_COLS)]

        # discard hidden players from scores -- in case a dummy casual player is added to represent a civilian
        for hidden_id in ASSASSINS_DATABASE.get_identifiers(include = lambda _: False,
                                                            include_hidden = lambda _: True):
            scores.pop(hidden_id, None)

        pseudonym_rows = []
        for (score, a_id) in sorted(((v, k) for (k, v) in scores.items()), reverse=True):
            # PSEUDONYM_ROW_TEMPLATE = "<tr {CREW_COLOR}><td>{RANK}</td><td>{PSEUDONYM}</td><td>{POINTS}</td><td>{MULTIPLIER}</td></tr>{TEAM_ENTRY}"
            team_id = member_to_team[a_id]
            crew_color = (CREW_COLOR_TEMPLATE.format(HEX=team_to_hex_col[team_id]) if team_id is not None else "")
            team_entry = (TEAM_ENTRY_TEMPLATE.format(TEAM=team_names[team_id], CREW_COLOR=crew_color) if team_id is not None else "")
            assassin = ASSASSINS_DATABASE.get(a_id)
            pseudonym_rows.append(
                PSEUDONYM_ROW_TEMPLATE.format(
                    CREW_COLOR=crew_color,
                    PSEUDONYM=assassin.all_pseudonyms(),
                    POINTS=score,
                    MULTIPLIER="Y" if a_id in multiplier_beneficiaries else "",
                    TEAM_ENTRY=team_entry
                )
            )

        player_rows = []
        for player in sorted(ASSASSINS_DATABASE.get_filtered(), key=lambda a: a.real_name.lower()):
            player_rows.append(
                PLAYER_ROW_TEMPLATE.format(
                    REAL_NAME = player.real_name,
                    PLAYER_TYPE = "Casual" if player.is_city_watch else "Full",
                    ADDRESS = player.address,
                    COLLEGE = player.college,
                    WATER_STATUS = player.water_status,
                    NOTES = player.notes
                )
            )

        with open(WEBPAGE_WRITE_LOCATION / "mw-players.html", "w+", encoding="utf-8") as F:
            F.write(MAYWEEK_PLAYERS_TEMPLATE.format(
                PSEUDONYM_ROWS = "\n".join(pseudonym_rows),
                PLAYER_ROWS = "\n".join(player_rows),
                YEAR = get_now_dt().year,
                MULTIPLIER_STR = self.gsdb_get("Multiplier", "Multiplier"),
                TEAM_COLUMN_HDR = TEAM_HDR_TEMPLATE.format(
                    TEAM_STR = self.get_cosmetic_name("Teams") if teams_enabled else ""
                )
            ))

        # may week news page

        # colour players by crew and don't do city watch, or inco colouring
        def mw_color_fn(pseudonym: str, assassin_model: Assassin, e: Event, managers: Sequence[Manager]) -> str:
            # render dead colour -- but only if died *in this event*
            if any(victim_id == assassin_model.identifier for (_, victim_id) in e.kills):
                return get_color(pseudonym, dead=True)

            # but otherwise use team colours,
            # getting the team from TeamManager
            team = None
            for manager in managers:
                if isinstance(manager, self.TeamManager):
                    team = manager.member_to_team[assassin_model.identifier]
                    break
            if team is not None:
                return team_to_hex_col[team]

            # fallback for individual
            return get_color(pseudonym)

        MAYWEEK_CHAPTER = Chapter("mw-news", "May Week News")

        generate_news_pages(
            headlines_path="mw-head.html",
            page_allocator=lambda e: MAYWEEK_CHAPTER if not e.pluginState.get("PageGeneratorPlugin", {}).get("hidden_event", False) else None,
            color_fn=mw_color_fn,
            plugin_managers=(self.TeamManager() for _ in range(teams_enabled))
        )

        return [Label("[MAY WEEK] Success!")]
