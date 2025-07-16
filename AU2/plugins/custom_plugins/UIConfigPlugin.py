from dataclasses import dataclass
from enum import Flag
from collections import namedtuple
from typing import Optional, Callable, List, Dict

from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.DependentComponents.AssassinPseudonymPair import AssassinPseudonymPair
from AU2.html_components.MetaComponents.ComponentOverride import ComponentOverride
from AU2.html_components.MetaComponents.Searchable import Searchable
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport
from AU2.plugins.CorePlugin import registered_plugin


class Call(Flag):
    NONE = 0
    EVENT_CREATE = 2 << 0
    EVENT_UPDATE = 2 << 1
    EVENT_DELETE = 2 << 2
    ASSASSIN_CREATE = 2 << 3
    ASSASSIN_UPDATE = 2 << 4
    ASSASSIN_STATUS = 2 << 5


EnabledFor = namedtuple("EnabledFor", ("call", "hooks"), defaults=(Call.NONE, tuple()))


@dataclass
class UIChange:
    """
    Represents a change in the UI to be applied across the tool.

    name (str): Name of this change to show in the UI
    replaces (str): Identifier of component to replace
    component (str): Replacement component
    enabled_for (EnabledFor): The calls/hooks for which this change should be enabled
    replacement_effects: A function to allow the new component to steal options/info from the replaced component.
                         First arg is old component, second is new component
    """
    name: str
    replaces: str
    component: HTMLComponent
    enabled_for: EnabledFor
    replacement_effects: Callable[[HTMLComponent, HTMLComponent], None] = lambda *args: None

    def set_status(self, enabled: List[str]):
        GENERIC_STATE_DATABASE.arb_state.setdefault("UIChanges", {})[self.replaces] = self.name in enabled

    def is_enabled(self):
        return GENERIC_STATE_DATABASE.arb_state.get("UIChanges", {}).get(self.replaces, False)

    def get_for_call(self, call: Call) -> Optional[ComponentOverride]:
        if call & self.enabled_for.call and self.is_enabled():
            return ComponentOverride(self.replaces, self.component, replacement_effects=self.replacement_effects)

    def get_for_hook(self, hook: str) -> Optional[ComponentOverride]:
        if self.is_enabled() and hook in self.enabled_for.hooks:
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
            new_comp.component.default = old_comp.default

        def filter_options(component, l):
            component.options = [o for o in component.options if o in l or o in component.defaults]

        def filter_input_dropdown(component, l):
            component.options = [o for o in component.options if o in l or o == component.selected]

        def steal_options(old_comp, new_comp):
            new_comp.component.options = old_comp.options
            new_comp.component.defaults = old_comp.defaults
            new_comp.component.title = old_comp.title

        def steal_input_dropdown_options(old_comp, new_comp):
            new_comp.component.options = old_comp.options
            new_comp.component.selected = old_comp.selected
            new_comp.component.title = old_comp.title

        self.ui_changes = [
            UIChange(
                name="Searchable Assassins (Events)",
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
                enabled_for=EnabledFor(call=Call.EVENT_CREATE | Call.EVENT_UPDATE, hooks=tuple()),
                replacement_effects=steal_assassins
            ),
            UIChange(
                name="Searchable Assassins (Hiding)",
                replaces="CorePlugin_hidden_assassins",
                component=Searchable(
                    component=SelectorList(
                        identifier="CorePlugin_hidden_assassins",
                        title="",
                        options=[]
                    ),
                    title="Enter assassin names to search for",
                    accessor=lambda component: sorted(component.options),
                    setter=filter_options
                ),
                enabled_for=EnabledFor(call=Call.NONE, hooks=("CorePlugin_hide_assassins",)),
                replacement_effects=steal_options
            ),
            UIChange(
                name="Searchable Assassins (Summary)",
                replaces="CorePlugin_assassin",
                component=Searchable(
                    component=InputWithDropDown(
                        identifier="CorePlugin_assassin",
                        title="",
                        options=[]
                    ),
                    title="Enter assassin names to search for",
                    accessor=lambda component: sorted(component.options),
                    setter=filter_input_dropdown
                ),
                enabled_for=EnabledFor(call=Call.ASSASSIN_STATUS, hooks=tuple()),
                replacement_effects=steal_input_dropdown_options
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

    def get_overrides_for_call(self, call: Call):
        comps = [c.get_for_call(call) for c in self.ui_changes]
        return [c for c in comps if c]

    def on_request_assassin_summary(self) -> List[HTMLComponent]:
        return self.get_overrides_for_call(Call.ASSASSIN_STATUS)

    def on_event_request_create(self, *_) -> List[HTMLComponent]:
        return self.get_overrides_for_call(Call.EVENT_CREATE)

    def on_event_request_update(self, *_) -> List[HTMLComponent]:
        return self.get_overrides_for_call(Call.EVENT_UPDATE)

    def on_event_request_delete(self, _: Event) -> List[HTMLComponent]:
        return self.get_overrides_for_call(Call.EVENT_DELETE)

    def on_assassin_request_create(self) -> List[HTMLComponent]:
        return self.get_overrides_for_call(Call.ASSASSIN_CREATE)

    def on_assassin_request_update(self, _: Assassin) -> List[HTMLComponent]:
        return self.get_overrides_for_call(Call.ASSASSIN_UPDATE)

    def on_request_hook_respond(self, hook: str) -> List[HTMLComponent]:
        comps = [c.get_for_hook(hook) for c in self.ui_changes]
        return [c for c in comps if c]
