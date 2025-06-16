import random
import datetime
from typing import List, Tuple, Any, Dict, Optional
from collections import Counter

from AU2.database.model.Event import Event
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.custom_plugins.PageGeneratorPlugin import HEX_COLS
from AU2.html_components.HTMLComponent import HTMLComponent
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.Table import Table
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.html_components.DependentComponents.AssassinDependentInputWithDropdown import AssassinDependentInputWithDropDown
from AU2.html_components.MetaComponents.Dependency import Dependency


def random_hexcode() -> str:
    return random.choice(HEX_COLS)


def normalise_hexcode(hexcode: str) -> str:
    hexcode = hexcode.upper()
    if hexcode[0] == "#":
        return hexcode[1:]
    else:
        return hexcode


class CrewManager:
    """
    Similar to CompetencyManager, DeathManager etc.
    This is defined within the MW2025 plugin as it probably should not be used outside of this.
    """
    def __init__(self):
        self.crew_map: Dict[str, str] = {}
        self.macguffins = Counter()

    def add_event(self, e: Event):
        crew_memb_changes = e.pluginState.get("MW2025Plugin", {}).get("MW2025Plugin_crew_membership_changes", {})
        crew_macguffin_gains = e.pluginState.get("MW2025Plugin", {}).get("MW2025Plugin_crew_macguffin_gains", {})
        crew_macguffin_losses = e.pluginState.get("MW2025Plugin", {}).get("MW2025Plugin_crew_macguffin_losses", {})
        self.crew_map.update(crew_memb_changes)
        self.macguffins.update(crew_macguffin_gains)
        self.macguffins.subtract(crew_macguffin_losses)

    def process_events_until(self, dt: Optional[datetime.datetime] = None) -> "CrewManager":
        for e in sorted(EVENTS_DATABASE.events.values(), key=lambda x: x.datetime):
            if dt and e.datetime > dt:
                break
            self.add_event(e)
        return self

    def member_map(self) -> Dict[str, str]:
        """Produces the 'inverse' of crew_map, i.e. a map from crews to a list of assassin identifiers"""
        memb_map: Dict[str, str] = {}
        for a, c in self.crew_map.items():
            memb_map.setdefault(c, []).append(a)
        return memb_map


@registered_plugin
class MW2025Plugin(AbstractPlugin):

    def __init__(self):
        super().__init__("MW2025Plugin")

        self.html_ids = {
            "Crew Name": self.identifier + "_crew_name",
            "Crew Colour": self.identifier + "_crew_colour",
            "Crew ID": self.identifier + "_crew_id",
            "Membership Changes": self.identifier + "_crew_membership_changes",
            "MacGuffin Gains": self.identifier + "_macguffin_gains",
            "MacGuffin Losses": self.identifier + "_macguffin_losses"
        }

        self.event_plugin_state = {
            "Membership Changes": {'id': self.identifier + "_crew_membership_changes", 'default': {}},
            "MacGuffin Gains": {'id': self.identifier + "_crew_macguffin_gains", 'default': []},
            "MacGuffin Losses": {'id': self.identifier + "_crew_macguffin_losses", 'default': []},
        }

        self.exports = [
            Export(
                "mw2025_edit_crews",
                "MW2025 -> Edit Crews",
                self.ask_edit_crews,
                self.answer_edit_crews,
                (self.gather_crews,)
            ),
            Export(
                "mw2025_crews_summary",
                "MW2025 -> Crews Summary",
                lambda: [],
                self.answer_crews_summary
            )
        ]

    def eps_get(self, event: Event, plugin_state_id: str) -> Any:
        return event.pluginState.get(self.identifier, {}).get(self.event_plugin_state[plugin_state_id]['id'],
                                                                  self.event_plugin_state[plugin_state_id][
                                                                      'default'])

    def eps_set(self, event: Event, plugin_state_id: str, data: Any):
        event.pluginState.setdefault(self.identifier, {})[self.event_plugin_state[plugin_state_id]['id']] = data

    # TODO: proper Crew handling a la Bounties in the old BountyPlugin
    def update_crew(self, crew_id: str, crew_name: str, crew_colour: str):
        GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {}).setdefault("CREWS", {})\
            .setdefault(crew_id, {}).update({"NAME": crew_name, "HEX": crew_colour})

    def get_crew(self, crew_id: str) -> Dict[str, str]:
        return self.get_crews().get(crew_id, {})

    def get_crews(self) -> Dict[str, Dict[str, str]]:
        return GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get("CREWS", {})

    def gather_crews(self) -> List[Tuple[str, str]]:
        crews = self.get_crews()
        return [("*NEW*", "")] + [(crew["NAME"], identifier) for identifier, crew in crews.items()]

    def ask_edit_crews(self, crew_id: str) -> List[HTMLComponent]:
        crew = self.get_crew(crew_id)
        crew_name = crew.get("NAME", "")
        crew_colour = crew.get("HEX", "")
        return [
            DefaultNamedSmallTextbox(self.html_ids["Crew Name"], "Crew name", crew_name),
            # TODO: Colour input HTMLComponent (to validate hexcode)
            DefaultNamedSmallTextbox(self.html_ids["Crew Colour"], "Crew colour hexcode (blank to randomise)", crew_colour),
            HiddenTextbox(self.html_ids["Crew ID"], crew_id)
        ]

    def answer_edit_crews(self, htmlResponse) -> List[HTMLComponent]:
        crew_id = htmlResponse[self.html_ids["Crew ID"]]
        crew_name = htmlResponse[self.html_ids["Crew Name"]]
        crew_colour = htmlResponse[self.html_ids["Crew Colour"]]

        # new crew case
        new = crew_id == ""
        if new:
            # generate a unique identifier for the crew a la Assassin / Event identifiers
            crew_id = f"({GENERIC_STATE_DATABASE.get_unique_str()}) {crew_name[:25].rstrip()}"

        # random colour gen
        if crew_colour == "":
            crew_colour = random_hexcode()

        self.update_crew(crew_id, crew_name, normalise_hexcode(crew_colour))
        return [
            Label(f"[MW2025] Created crew {crew_name}.") if new
            else Label(f"[MW2025] Updated crew {crew_name}.")
        ]


    def answer_crews_summary(self, htmlResponse) -> List[HTMLComponent]:
        rows = []
        crew_manager = CrewManager().process_events_until()
        member_map = crew_manager.member_map()
        for crew_id, members in sorted(member_map.items(), key=lambda x: self.get_crew(x[0]).get("NAME", "").lower()):
            crew_name = self.get_crew(crew_id).get("NAME", "")
            crew_macguffins = crew_manager.macguffins[crew_id]
            if not crew_name:
                continue
            for member in members:
                rows.append([crew_name, member, crew_macguffins])
                # "merge" rows in the crew name and macguffin (mythic compass) status columns
                crew_name = ""
                crew_macguffins = ""
        print(rows)
        return [
            Table(
                rows or [[]],
                headings=["Crew" + " "*50, "Members" + " "*50, "Mythic Compasses"]
            )
        ]

    def on_event_request_create(self) -> List[HTMLComponent]:
        crew_options = [(crew["NAME"], ident) for ident, crew in self.get_crews().items()]
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentInputWithDropDown(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Membership Changes"],
                        title="Crews: select players who changed crew",
                        options=[("(Individual)", ""),
                                 *((crew["NAME"], identifier) for identifier, crew in self.get_crews().items())],
                    )
                ]
            ),
            # possible TODO: allow the macguffin to be renamed by config
            SelectorList(self.html_ids["MacGuffin Gains"],
                         title="Select crews who GAINED a mythic compass",
                         options=crew_options),
            SelectorList(self.html_ids["MacGuffin Losses"],
                         title="Select crews who LOST a mythic compass",
                         options=crew_options),
        ]


    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        self.eps_set(e, "Membership Changes", htmlResponse[self.html_ids["Membership Changes"]])
        self.eps_set(e, "MacGuffin Gains", htmlResponse[self.html_ids["MacGuffin Gains"]])
        self.eps_set(e, "MacGuffin Losses", htmlResponse[self.html_ids["MacGuffin Losses"]])
        return [Label("[MW2025] Success!")]


    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        crew_options = [(crew["NAME"], ident) for ident, crew in self.get_crews().items()]
        macguffin_gains = self.eps_get(e, "MacGuffin Gains")
        macguffin_losses = self.eps_get(e, "MacGuffin Losses")
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentInputWithDropDown(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.html_ids["Membership Changes"],
                        title="Crews: select players who changed crew",
                        options=[("(Individual)", ""), *((crew["NAME"], identifier)
                                                         for identifier, crew in self.get_crews().items())],
                        default=self.eps_get(e, "Membership Changes")
                    )
                ]
            ),
            SelectorList(self.html_ids["MacGuffin Gains"],
                         title="Select crews who GAINED a mythic compass",
                         options=crew_options,
                         defaults=macguffin_gains),
            SelectorList(self.html_ids["MacGuffin Losses"],
                         title="Select crews who LOST a mythic compass",
                         options=crew_options,
                         defaults=macguffin_losses),
        ]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        self.eps_set(e, "Membership Changes", htmlResponse[self.html_ids["Membership Changes"]])
        self.eps_set(e, "MacGuffin Gains", htmlResponse[self.html_ids["MacGuffin Gains"]])
        self.eps_set(e, "MacGuffin Losses", htmlResponse[self.html_ids["MacGuffin Losses"]])
        return [Label("[MW2025] Success!")]
