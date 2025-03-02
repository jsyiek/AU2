from dataclasses import dataclass
from enum import Flag
from collections import namedtuple
from typing import Optional, Callable, List, Union

from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.DependentComponents.AssassinPseudonymPair import AssassinPseudonymPair
from AU2.html_components.MetaComponents.ComponentOverride import ComponentOverride
from AU2.html_components.MetaComponents.Searchable import Searchable
from AU2.html_components.MetaComponents.ForEach import ForEach
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport
from AU2.plugins.CorePlugin import registered_plugin


class Call(Flag):
    NONE = 0
    EVENT_CREATE = 1
    EVENT_UPDATE = 2
    EVENT_DELETE = 4
    ASSASSIN_CREATE = 8
    ASSASSIN_UPDATE = 16
    GATHER_ASSASSIN_PSEUDONYM_PAIRS = 32

EnabledFor = namedtuple("EnabledFor", ("call", "hooks"), defaults=(Call.NONE, tuple()))

@dataclass
class UIChange:
    name: str
    replaces: str
    replacement_factory: Callable[[HTMLComponent], HTMLComponent]
    enabled_for: EnabledFor

    def set_status(self, enabled: List[str]):
        GENERIC_STATE_DATABASE.arb_state.setdefault("UIChanges", {})[self.replaces] = self.name in enabled

    def is_enabled(self):
        return GENERIC_STATE_DATABASE.arb_state.get("UIChanges", {}).get(self.replaces, False)

    def get_for_call(self, call: Call) -> Optional[ComponentOverride]:
        if call & self.enabled_for.call and self.is_enabled():
            return ComponentOverride(self.replaces, replacement_factory=self.replacement_factory)

    def get_for_hook(self, hook: str) -> Optional[ComponentOverride]:
        if self.is_enabled() and hook in self.enabled_for.hooks:
            return ComponentOverride(self.replaces, replacement_factory=self.replacement_factory)


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

        def filter_options(component: Union[SelectorList, ForEach], l: List[str]):
            component.options = [o for o in component.options if o in l or o in component.defaults]

        def assassin_selector_to_searchable(old_component: Union[SelectorList, ForEach]) -> Searchable:
            return Searchable(
                component=old_component,
                title="Enter assassin names to search for",
                accessor=lambda component: sorted(component.options),
                setter=filter_options
            )

        self.ui_changes = [
            UIChange(
                name="Searchable Assassins (Events)",
                replaces="assassin_selection",
                replacement_factory=assassin_selector_to_searchable,
                enabled_for=EnabledFor(call=Call.GATHER_ASSASSIN_PSEUDONYM_PAIRS),
            ),
            UIChange(
                name="Searchable Assassins (Hiding)",
                replaces="CorePlugin_hidden_assassins",
                replacement_factory=assassin_selector_to_searchable,
                enabled_for=EnabledFor(hooks=("CorePlugin_hide_assassins",))
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

    def on_gather_assassin_pseudonym_pairs(self, *_) -> List[HTMLComponent]:
        return self.get_overrides_for_call(Call.GATHER_ASSASSIN_PSEUDONYM_PAIRS)

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
