from dataclasses import dataclass
from enum import Flag
from typing import Optional, Callable, List, Dict

from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.DependentComponents.AssassinPseudonymPair import AssassinPseudonymPair
from AU2.html_components.MetaComponents.ComponentOverride import ComponentOverride
from AU2.html_components.MetaComponents.Searchable import Searchable
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport
from AU2.plugins.CorePlugin import registered_plugin


class Call(Flag):
    EVENT_CREATE = 1
    EVENT_UPDATE = 2
    EVENT_DELETE = 4
    ASSASSIN_CREATE = 8
    ASSASSIN_UPDATE = 16


@dataclass
class UIChange:
    name: str
    replaces: str
    component: HTMLComponent
    enabled_for: Call
    replacement_effects: Callable[[HTMLComponent, HTMLComponent], None] = lambda *args: None

    def set_status(self, enabled: List[str]):
        GENERIC_STATE_DATABASE.arb_state.setdefault("UIChanges", {})[self.replaces] = self.name in enabled

    def is_enabled(self):
        return GENERIC_STATE_DATABASE.arb_state.get("UIChanges", {}).get(self.replaces, False)

    def get(self, call: Call) -> Optional[ComponentOverride]:
        if call & self.enabled_for and self.is_enabled():
            return ComponentOverride(self.replaces, self.component, replacement_effects=self.replacement_effects)


@registered_plugin
class UIConfigPlugin(AbstractPlugin):

    def __init__(self):
        super().__init__("UIConfigPlugin")

        self.html_ids = {}

        self.config_exports = [
            ConfigExport(
                "uiconfig_toggle_changes",
                "UI Config -> Toggle UI options",
                self.ask_toggle_parameters,
                self.answer_toggle_parameters
            )
        ]

        def filter_assassin_list(component, l):
            component.assassins = [a for a in component.assassins if a[0] in l]

        def steal_assassins(old_comp, new_comp):
            new_comp.component.assassins = old_comp.assassins

        self.ui_changes = [
            UIChange(
                name="Searchable Assassins",
                replaces="CorePlugin_assassin_pseudonym",
                component=Searchable(
                    component=AssassinPseudonymPair(
                        "CorePlugin_assassin_pseudonym",
                        assassins=[],
                        title=""
                    ),
                    title="Enter assassin names to search for",
                    accessor=lambda component: sorted([a[0] for a in component.assassins]),
                    setter=filter_assassin_list
                ),
                enabled_for=Call.EVENT_CREATE | Call.EVENT_UPDATE,
                replacement_effects=steal_assassins
            )
        ]

    def ask_toggle_parameters(self):
        return [
            SelectorList(
                identifier="config",
                title="Enable/disable UI changes",
                options=[ui_change.name for ui_change in self.ui_changes],
                defaults=[ui_change.name for ui_change in self.ui_changes if ui_change.is_enabled()]
            )
        ]

    def answer_toggle_parameters(self, html_response):
        for ui_change in self.ui_changes:
            ui_change.set_status(html_response["config"])
        return [Label("[UIConfig] Success!")]

    def get_calls(self, call: Call):
        comps = [c.get(call) for c in self.ui_changes]
        return [c for c in comps if c]

    def on_event_request_create(self) -> List[HTMLComponent]:
        return self.get_calls(Call.EVENT_CREATE)

    def on_event_request_update(self, _: Event) -> List[HTMLComponent]:
        return self.get_calls(Call.EVENT_UPDATE)

    def on_event_request_delete(self, _: Event) -> List[HTMLComponent]:
        return self.get_calls(Call.EVENT_DELETE)

    def on_assassin_request_create(self) -> List[HTMLComponent]:
        return self.get_calls(Call.ASSASSIN_CREATE)

    def on_assassin_request_update(self, _: Assassin) -> List[HTMLComponent]:
        return self.get_calls(Call.ASSASSIN_UPDATE)
