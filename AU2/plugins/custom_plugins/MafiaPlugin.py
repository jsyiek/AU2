from typing import List

from AU2.database.model import Assassin, Event
from AU2.html_components import HTMLComponent
from AU2.html_components.AssassinDependentIntegerEntry import AssassinDependentIntegerEntry
from AU2.html_components.AssassinDependentSelector import AssassinDependentSelector
from AU2.html_components.Dependency import Dependency
from AU2.html_components.InputWithDropDown import InputWithDropDown
from AU2.html_components.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin


MAFIAS = [
    "The Crazy 88",
    "The Vengeance Pact",
    "The Family"
]

CAPODECINA_MULTIPLIER = 1.25


class MafiaPlugin(AbstractPlugin):

    def __init__(self):
        super().__init__("MafiaPlugin")

        self.html_ids = {
            "Mafia": self.identifier + "_mafia",
            "Capodecina": self.identifier + "_capodecina",
            "Points": self.identifier + "_points",
        }

        self.plugin_state = {
            "MAFIA": "mafia",
            "CAPODECINA": "capodecina",
            "POINTS": "points"
        }

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
                    )
                ]
            )
        ]

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})[self.plugin_state["CAPODECINA"]] = \
            htmlResponse[self.html_ids["Capodecina"]]
        e.pluginState[self.identifier][self.plugin_state["POINTS"]] = \
            htmlResponse[self.html_ids["Points"]]

        return [Label("[MAFIA] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        capodecina = e.pluginState.get(self.identifier, {}).get(self.plugin_state["CAPODECINA"], None)
        points = e.pluginState.get(self.identifier, {}).get(self.plugin_state["POINTS"], None)
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
                    )
                ]
            )
        ]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})[self.plugin_state["CAPODECINA"]] = \
            htmlResponse[self.html_ids["Capodecina"]]
        e.pluginState[self.identifier][self.plugin_state["POINTS"]] = \
            htmlResponse[self.html_ids["Points"]]

        return [Label("[MAFIA] Success!")]

