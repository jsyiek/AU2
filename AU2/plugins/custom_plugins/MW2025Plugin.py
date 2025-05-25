import random
from typing import List, Tuple

from AU2.database.model.Event import Event
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.custom_plugins.PageGeneratorPlugin import HEX_COLS
from AU2.html_components.HTMLComponent import HTMLComponent
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.Label import Label


def random_hexcode() -> str:
    return random.choice(HEX_COLS)


def normalise_hexcode(hexcode: str) -> str:
    hexcode = hexcode.upper()
    if hexcode[0] == "#":
        return hexcode[1:]
    else:
        return hexcode


@registered_plugin
class MW2025Plugin(AbstractPlugin):

    def __init__(self):
        super().__init__("MW2025Plugin")

        self.html_ids = {
            "Crew Name": self.identifier + "_crew_name",
            "Crew Colour": self.identifier + "_crew_colour",
            "Crew ID": self.identifier + "_crew_id"
        }

        self.exports = [
            Export(
                "mw2025_edit_crews",
                "MW2025 -> Edit Crews",
                self.ask_edit_crews,
                self.answer_edit_crews,
                (self.gather_crews,)
            )
        ]

    def update_crew(self, crew_id: str, crew_name: str, crew_colour: str):
        GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {}).setdefault("CREWS", {})\
            .setdefault(crew_id, {}).update({"NAME": crew_name, "HEX": crew_colour})

    def gather_crews(self) -> List[Tuple[str, str]]:
        crews = GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get("CREWS", {})
        return [("*NEW*", "")] + [(crew["NAME"], identifier) for identifier, crew in crews.items()]

    def ask_edit_crews(self, crew_id: str) -> List[HTMLComponent]:
        crew = GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get("CREWS", {}).get(crew_id, {})
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


    def on_event_request_create(self) -> List[HTMLComponent]:
        return [
            # TODO: create a 'AssassinDependentDropdown' component,
            #       which will be used to assign new crews to players.
        ]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        return []

