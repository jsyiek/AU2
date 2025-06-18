import dataclasses
from typing import List, Dict, Set

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.html_components.DependentComponents.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.DependentComponents.AssassinDependentTransferEntry import AssassinDependentTransferEntry
from AU2.html_components.DependentComponents.KillDependentSelector import KillDependentSelector
from AU2.html_components.MetaComponents.Dependency import Dependency
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.IntegerEntry import IntegerEntry
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.LargeTextEntry import LargeTextEntry
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport, Export
from AU2.plugins.CorePlugin import registered_plugin


HEX_COLS = [
    '#00A6A3', '#26CCC8', '#008B8A', '#B69C1F',
    '#D1B135', '#5B836E', '#7A9E83', '#00822b',
    '#00A563', '#FFA44D', '#CC6C1E', '#37b717',
    '#27B91E', '#1F9E1A', '#3DC74E', '#00c6c3',
    '#b7a020', '#637777', '#f28110'
]

CREW_COLOR_TEMPLATE = 'bgcolor="{HEX}"'
TEAM_ENTRY_TEMPLATE = "<td>{TEAM}</td>"
PLAYER_ROW_TEMPLATE = "<tr><td>{REAL_NAME}</td><td>{PLAYER_TYPE}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{NOTES}</td></tr>"
PSEUDONYM_ROW_TEMPLATE = "<tr {CREW_COLOR}><td>{PSEUDONYM}</td><td>{POINTS}</td><td>{MULTIPLIER}</td></tr>{TEAM_ENTRY}"

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

    **Casual players**: This is a cosmetic change; police players are referred to as
                        'casual'.

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
            "Assassins": self.identifier + "_assassins",
            "Team ID": self.identifier + "_team_id",
            "Multiplier Transfer": self.identifier + "_multiplier_transfer",
            "Kills as Team": self.identifier + "_kills_as_team",
            "BS Points": self.identifier + "_bs_points",
        }

        self.plugin_state = {
            "Team Names": "team_names",
            "Enable Teams?": "enable_teams",
            "Share Multipliers?": "share_multipliers",
            "Team Members": "team_members",
            "Multiplier Transfers": "multiplier_transfers",
            "Kills as Team": "kills_as_team",
            "BS Points": "bs_points",
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
            # this would have been nice to be a DCE, but we really need gather here
            Export(
                "may_week_assign_teams",
                "May Week -> Assign players to teams",
                self.ask_assign_teams,
                self.answer_assign_teams,
                (self.gather_assign_teams,)
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

    def gsdb_get(self, plugin_state_id, default):
        return GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get(self.plugin_state[plugin_state_id], default)

    def gsdb_set(self, plugin_state_id, data):
        GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {})[self.plugin_state[plugin_state_id]] = data

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
            checked=self.gsdb_get("Share Multipliers?", False)
        )]

    def answer_enable_multiplier_team_sharing(self, html_response):
        enabled = html_response[self.html_ids["Share Multipliers?"]]
        self.gsdb_set("Share Multipliers?", enabled)
        return [
            Label("Team multiplier sharing is now: " + "enabled" if enabled else "disabled")
        ]

    def ask_name_teams(self):
        existing_ranks: List[str] = self.gsdb_get("Team Names", ["Team 1", "Team 2", "Team 3"])
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
            map(str.split,
                filter(lambda t: not t.strip().startswith("#"),
                       html_response[self.html_ids["Team Names"]].split("\n"))))
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
            self.gsdb_set(param.identifier(), html_response[self.html_ids[param.name]])

        return [
            Label(title=f"Parameter {param.name} set to {html_response[self.html_ids[param.name]]}")
            for param in self.scoring_parameters
        ]

    def gather_assign_teams(self):
        return self.gsdb_get("Team Names", ["Team 1", "Team 2", "Team 3"])

    def ask_assign_teams(self, team_name: str):
        team_id: int = self.gsdb_get("Team Names", ["Team 1", "Team 2", "Team 3"]).index(team_name)
        members: List[str] = self.gsdb_get("Team Members", {}).get(team_id, [])
        return [
            HiddenTextbox(identifier=self.html_ids["Team ID"], default=str(team_id)),
            SelectorList(
                identifier=self.html_ids["Assassins"],
                title=f"Select team members for {team_name}",
                options=ASSASSINS_DATABASE.get_identifiers(),
                defaults=members
            )
        ]

    def answer_assign_teams(self, html_response):
        members: List[str] = html_response[self.html_ids["Assassins"]]
        team_id: int = int(html_response[self.html_ids["Team ID"]])
        team_map: Dict[int, List[str]] = self.gsdb_get("Team Members", {})
        team_map[team_id] = members
        self.gsdb_set("Team Members", team_map)
        return [
            Label("Team mapping updated!")
        ]

    def get_cosmetic_name(self, name: str) -> str:
        return self.gsdb_get(name, name.lower())

    def get_multiplier_owners(self, max_event: int = float("inf")) -> List[str]:
        owners = set()
        for event in EVENTS_DATABASE.events.values():
            if int(event._Event__secret_id) > max_event:
                continue
            key = self.plugin_state["Multiplier Transfers"]
            for (loser, gainer) in event.pluginState.get(self.identifier, {}).get(key, []):
                if loser is not None and loser in owners:
                    owners.remove(loser)
                if gainer is not None:
                    owners.add(gainer)
        return list(owners)

    def on_event_request_create(self) -> List[HTMLComponent]:
        multiplier_str = self.get_cosmetic_name("Multiplier").lower()
        teams_str = self.get_cosmetic_name("Teams").lower()
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentIntegerEntry(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["BS Points"],
                        title="Want to award any BS points?"
                    ),
                    AssassinDependentTransferEntry(
                        assassins_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Multiplier Transfer"],
                        owners=self.get_multiplier_owners(),
                        title=f"[MAY WEEK] Any {multiplier_str} transfers? (None -> A adds a new {multiplier_str}, A -> None deletes it)"
                    ),
                ]
            ),
            *(KillDependentSelector(
                identifier=self.html_ids["Kills as Team"],
                kills_identifier="CorePlugin_kills",
                title=f"[MAY WEEK] Which kills were made in a {teams_str}, for the purposes of scoring?"
            ) for _ in range(self.gsdb_get("Enable Teams?", False)))
        ]

    def on_event_create(self, e: Event, html_response) -> List[HTMLComponent]:
        e.pluginState[self.identifier][self.plugin_state["Multiplier Transfer"]] = html_response[self.html_ids["Multiplier Transfer"]]
        e.pluginState[self.identifier][self.plugin_state["Kills as Team"]] = html_response[self.html_ids["Kills as Team"]]
        e.pluginState[self.identifier][self.plugin_state["BS Points"]] = html_response[self.html_ids["BS Points"]]
        return [Label("[MAY WEEK] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        multiplier_str = self.get_cosmetic_name("Multiplier").lower()
        teams_str = self.get_cosmetic_name("Teams").lower()
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentIntegerEntry(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["BS Points"],
                        title="Want to award any BS points?",
                        default=e.pluginState.get(self.identifier, {}).get(self.plugin_state["BS Points"], {})
                    ),
                    Label(f"[MAY WEEK] WARNING! Changing this will not play nicely if the {multiplier_str} has already "
                          "transferred again after this!"),
                    AssassinDependentTransferEntry(
                        assassins_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Multiplier Transfer"],
                        owners=self.get_multiplier_owners(max_event=int(e._Event__secret_id)),
                        title=f"[MAY WEEK] Any {multiplier_str} transfers?"
                    ),
                    Dependency(
                        dependentOn="CorePlugin_kills",
                        htmlComponents=[
                            *(KillDependentSelector(
                                identifier=self.html_ids["Kills as Team"],
                                kills_identifier="CorePlugin_kills",
                                title=f"[MAY WEEK] Which kills were made in a {teams_str}, for the purposes of scoring?",
                                default=e.pluginState.get(self.identifier, {}).get(self.plugin_state["Kills as Team"], [])
                            ) for _ in range(self.gsdb_get("Enable Teams?", False)))
                        ]
                    )
                ]
            ),
        ]

    def on_event_update(self, e: Event, html_response) -> List[HTMLComponent]:
        self.gsdb_set("Multiplier Transfers", html_response[self.html_ids["Multiplier Transfer"]])
        self.gsdb_set("BS Points",  html_response[self.html_ids["BS Points"]])
        if self.html_ids["Kills as Team"] in html_response:
            self.gsdb_set("Kills as Team", html_response[self.html_ids["Kills as Team"]])
        return [Label("[MAY WEEK] Success!")]

    def calculate_scores_and_multiplier_state(self, max_event: int = float("inf")) -> (Dict[str, float], Set[str], Set[str]):
        """
        Calculates the scores and multiplier owners up to a given event.

        Args:
            max_event: the secret id of the last event to process (note: events are processed in order of secret id
                (i.e. the order they were created) rather than by datetime

        Returns:
            (Dict[str, float], Set[str]): A tuple of
                - A dictionary mapping assassin identifiers to their scores
                - A set of multiplier owners
                - A set of those benefiting from multipliers via their teams
        """
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

        scores: Dict[str, float] = {a.identifier: Sf if not a.is_police else Sc for a in ASSASSINS_DATABASE.get_filtered(
            include_hidden = lambda _: True # probably not necessary in May Week (since no resurrection as police),
                                            # but just in case...
        )}
        multiplier_owners = set()
        teams_enabled = self.gsdb_get("Enable Teams?", False)
        team_multiplier_sharing_enabled = teams_enabled and self.gsdb_get("Share Multipliers?", False)
        team_to_members = self.gsdb_get("Team Members", {})
        members_to_teams = {}
        for (t, member_list) in team_to_members.items():
            for m in member_list:
                members_to_teams.setdefault(m, set()).add(t)

        for e in EVENTS_DATABASE.events.values():
            if int(e._Event__secret_id) > max_event:
                continue

            kills_made_as_team = e.pluginState.get(self.identifier, {}).get(self.plugin_state["Kills as Team"], [])
            bs_points = e.pluginState.get(self.identifier, {}).get(self.plugin_state["BS Points"], {}).items()

            # updates happen atomically, so we calculate them as a batch and then add them back in
            point_deltas = {player: bs_allotment for (player, bs_allotment) in bs_points}

            for (killer, victim) in e.kills:
                is_as_team = teams_enabled and (killer, victim) in kills_made_as_team
                is_with_multiplier = killer in multiplier_owners

                if team_multiplier_sharing_enabled and not is_with_multiplier:
                    for owner in multiplier_owners:
                        is_with_multiplier |= len(members_to_teams[owner].intersection(members_to_teams[killer])) > 0

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

        multiplier_beneficiaries = {members_to_teams[owner] for owner in multiplier_owners}

        return scores, multiplier_owners, multiplier_beneficiaries

    def on_page_generate(self, htmlResponse) -> List[HTMLComponent]:
        scores, multiplier_owners, multiplier_beneficiaries = self.calculate_scores_and_multiplier_state()
        teams_enabled = self.gsdb_get("Enable Teams?", False)
        team_to_members = self.gsdb_get("Team Members", {})
        members_to_teams = {}
        for (t, member_list) in team_to_members.items():
            for m in member_list:
                members_to_teams.setdefault(m, set()).add(t)

        team_to_hex_col = {}
        for (i, team) in enumerate(team_to_members):
            team_to_hex_col[team] = HEX_COLS[i % len(HEX_COLS)]

        player_rows = []
        pseudonym_rows = []
        for (score, a_id) in sorted((v, k) for (k, v) in scores.items()):
            # PSEUDONYM_ROW_TEMPLATE = "<tr {CREW_COLOR}><td>{RANK}</td><td>{PSEUDONYM}</td><td>{POINTS}</td><td>{MULTIPLIER}</td></tr>{TEAM_ENTRY}"
            team = next(iter(members_to_teams[a_id])) if teams_enabled and members_to_teams.get(a_id, []) else ""
            crew_color = (CREW_COLOR_TEMPLATE.format(HEX=team_to_hex_col[team]) if team else "")
            team_entry = (TEAM_ENTRY_TEMPLATE.format(TEAM=team) if team else "")
            assassin = ASSASSINS_DATABASE.get(a_id)
            pseudonym_rows.append(
                PSEUDONYM_ROW_TEMPLATE.format(
                    CREW_COLOR=crew_color,
                    PSEUDONYM=assassin.all_pseudonyms(),
                    POINTS=score,
                    MULTIPLIER="Y" if a_id in multiplier_owners else "N",
                    TEAM_ENTRY = team_entry
                )
            )
        #for a in ASSASSINS_DATABASE.get_filtered():
            #pseudo

        return [Label("[MAY WEEK] Success!")]