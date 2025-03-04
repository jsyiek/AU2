import glob
import os.path

from typing import Dict, List, Tuple, Any, Optional
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Assassin, Event
from AU2.html_components import HTMLComponent
from AU2.html_components.SpecialComponents.EditablePseudonymList import EditablePseudonymList, PseudonymData
from AU2.html_components.SpecialComponents.ConfigOptionsList import ConfigOptionsList
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.DatetimeEntry import DatetimeEntry
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.HiddenJSON import HiddenJSON
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.LargeTextEntry import LargeTextEntry
from AU2.html_components.SimpleComponents.NamedSmallTextbox import NamedSmallTextbox
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.html_components.MetaComponents.Dependency import Dependency
from AU2.html_components.MetaComponents.ForEach import ForEach
from AU2.plugins import CUSTOM_PLUGINS_DIR
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export, ConfigExport, HookedExport, DangerousConfigExport
from AU2.plugins.AvailablePlugins import __PluginMap
from AU2.plugins.constants import COLLEGES, WATER_STATUSES
from AU2.plugins.sanity_checks import SANITY_CHECKS
from AU2.plugins.util.game import get_game_start, set_game_start


AVAILABLE_PLUGINS = {}


def registered_plugin(plugin_class):
    plugin = plugin_class()
    AVAILABLE_PLUGINS[plugin.identifier] = plugin
    return plugin_class


for file in glob.glob(os.path.join(CUSTOM_PLUGINS_DIR, "*.py")):
    name = os.path.splitext(os.path.basename(file))[0]
    module = __import__(f"AU2.plugins.custom_plugins.{name}")


PLUGINS = __PluginMap(AVAILABLE_PLUGINS)


@registered_plugin
class CorePlugin(AbstractPlugin):

    PLUGIN_ENABLE_EXPORT: str = "core_plugin_config_update"
    CONFIG_PARAMETER_EXPORT: str = "core_plugin_edit_config"
    IRREMOVABLE_EXPORTS = [PLUGIN_ENABLE_EXPORT, CONFIG_PARAMETER_EXPORT]

    def __init__(self):
        super().__init__("CorePlugin")
        self.HTML_SECRET_ID = "CorePlugin_identifier"

        self.html_ids = {
            "Pseudonym": self.identifier + "_pseudonym",
            "Real Name": self.identifier + "_real_name",
            "Pronouns": self.identifier + "_pronouns",
            "Email": self.identifier + "_email",
            "Address": self.identifier + "_address",
            "Water Status": self.identifier + "_water_status",
            "College": self.identifier + "_college",
            "Notes": self.identifier + "_notes",
            "Police": self.identifier + "_police",
            "Hidden Assassins": self.identifier + "_hidden_assassins"
        }

        self.params = {
            self.html_ids["Pseudonym"]: "pseudonyms",
            self.html_ids["Real Name"]: "real_name",
            self.html_ids["Pronouns"]: "pronouns",
            self.html_ids["Address"]: "address",
            self.html_ids["Email"]: "email",
            self.html_ids["Water Status"]: "water_status",
            self.html_ids["College"]: "college",
            self.html_ids["Notes"]: "notes",
            self.html_ids["Police"]: "is_police"
        }

        self.event_html_ids = {
            "Assassin Pseudonym": self.identifier + "_assassin_pseudonym",
            "Datetime": self.identifier + "_datetime",
            "Headline": self.identifier + "_headline",
            "Reports": self.identifier + "_reports",
            "Kills": self.identifier + "_kills"
        }

        self.event_params = {
            self.event_html_ids["Assassin Pseudonym"]: "assassins",
            self.event_html_ids["Datetime"]: "datetime",
            self.event_html_ids["Headline"]: "headline",
            self.event_html_ids["Kills"]: "kills"
        }

        self.config_html_ids = {
            "Suppressed Exports": self.identifier + "_suppressed_exports",
            "Pinned Exports": self.identifier + "_pinned_exports"
        }

        self.exports = [
            Export(
                "core_assassin_create_assassin",
                "Assassin -> Create",
                self.ask_core_plugin_create_assassin,
                self.answer_core_plugin_create_assassin
            ),
            Export(
                "core_assassin_update_assassin",
                "Assassin -> Update",
                self.ask_core_plugin_update_assassin,
                self.answer_core_plugin_update_assassin,
                ((lambda: ASSASSINS_DATABASE.get_identifiers()),)
            ),
            Export(
                "core_event_create_event",
                "Event -> Create",
                self.ask_core_plugin_create_event,
                self.answer_core_plugin_create_event,
                (self.gather_assassin_pseudonym_pairs,)
            ),
            Export(
                "core_event_delete_event",
                "Event -> Delete",
                self.ask_core_plugin_delete_event,
                self.answer_core_plugin_delete_event,
                (self.gather_events,)
            ),
            Export(
                "core_event_update_event",
                "Event -> Update",
                self.ask_core_plugin_update_event,
                self.answer_core_plugin_update_event,
                (self.gather_events, self.gather_assassin_pseudonym_pairs)
            ),
            Export(
                self.PLUGIN_ENABLE_EXPORT,
                "Plugin config -> Enable/disable plugins",
                self.ask_core_plugin_update_config,
                self.answer_core_plugin_update_config
            ),
            Export(
                "core_plugin_generate_pages",
                "Generate pages",
                self.ask_generate_pages,
                self.answer_generate_pages
            ),
            Export(
                self.CONFIG_PARAMETER_EXPORT,
                "Plugin config -> Plugin-specific parameters",
                self.ask_config,
                self.answer_config,
                (self.gather_config_options,)
            )
        ]

        self.hooks = {
            "hide_assassins": self.identifier + "_hide_assassins",
        }

        self.hooked_exports = [
            HookedExport(
                plugin_name=self.identifier,
                identifier=self.hooks["hide_assassins"],
                display_name="Assassin -> Hide",
                producer=lambda x: None,
                call_order=HookedExport.LAST
            )
        ]

        self.config_exports = [
            DangerousConfigExport(
                "core_plugin_set_game_start",
                "CorePlugin -> Set game start",
                self.ask_set_game_start,
                self.answer_set_game_start
            ),
            ConfigExport(
                "core_plugin_suppress_exports",
                "CorePlugin -> Hide menu options",
                self.ask_suppress_exports,
                self.answer_suppress_exports
            ),
            ConfigExport(
                "core_plugin_reorder_exports",
                "CorePlugin -> Pin menu options",
                self.ask_reorder_exports,
                self.answer_reorder_exports
            )
        ]

    def on_assassin_request_create(self):
        html = [
            NamedSmallTextbox(self.html_ids["Pseudonym"], "Initial Pseudonym"),
            NamedSmallTextbox(self.html_ids["Real Name"], "Real Name"),
            NamedSmallTextbox(self.html_ids["Pronouns"], "Pronouns"),
            NamedSmallTextbox(self.html_ids["Email"], "Email", type_="email"),
            NamedSmallTextbox(self.html_ids["Address"], "Address"),
            InputWithDropDown(self.html_ids["Water Status"], "Water Status", WATER_STATUSES),
            InputWithDropDown(self.html_ids["College"], "College", COLLEGES),
            LargeTextEntry(self.html_ids["Notes"], "Notes"),
            Checkbox(self.html_ids["Police"], "Police? (y/n)")
        ]
        return html

    def on_assassin_create(self, assassin: Assassin, htmlResponse) -> List[HTMLComponent]:
        return [Label("[CORE] Success!")]

    def on_assassin_request_update(self, assassin: Assassin):
        html = [
            HiddenTextbox(self.HTML_SECRET_ID, assassin.identifier),
            Label("Assassin type: " + ("Police" if assassin.is_police else "Full Player")),
            EditablePseudonymList(
                self.html_ids["Pseudonym"], "Edit Pseudonyms",
                (PseudonymData(p, assassin.get_pseudonym_validity(i)) for i, p in enumerate(assassin.pseudonyms))
            ),
            DefaultNamedSmallTextbox(self.html_ids["Real Name"], "Real Name", assassin.real_name),
            DefaultNamedSmallTextbox(self.html_ids["Pronouns"], "Pronouns", assassin.pronouns),
            DefaultNamedSmallTextbox(self.html_ids["Email"], "Email", assassin.email, type_="email"),
            DefaultNamedSmallTextbox(self.html_ids["Address"], "Address", assassin.address),
            InputWithDropDown(self.html_ids["Water Status"], "Water Status", WATER_STATUSES, selected=assassin.water_status),
            InputWithDropDown(self.html_ids["College"], "College", COLLEGES, selected=assassin.college),
            LargeTextEntry(self.html_ids["Notes"], "Notes", default=assassin.notes),
        ]
        return html

    def on_assassin_update(self, assassin: Assassin, htmlResponse: Dict) -> List[HTMLComponent]:
        # process updates to the assassin's pseudonyms
        pseudonym_updates = htmlResponse[self.html_ids["Pseudonym"]]
        [assassin.add_pseudonym(u.text, u.valid_from) for u in pseudonym_updates.new_values]
        [assassin.edit_pseudonym(i, v.text, v.valid_from) for i, v in pseudonym_updates.edited.items()]
        [assassin.delete_pseudonym(i) for i in pseudonym_updates.deleted_indices]
        # set other attributes
        assassin.real_name = htmlResponse[self.html_ids["Real Name"]]
        assassin.pronouns = htmlResponse[self.html_ids["Pronouns"]]
        assassin.email = htmlResponse[self.html_ids["Email"]]
        assassin.address = htmlResponse[self.html_ids["Address"]]
        assassin.water_status = htmlResponse[self.html_ids["Water Status"]]
        assassin.college = htmlResponse[self.html_ids["College"]]
        assassin.notes = htmlResponse[self.html_ids["Notes"]]
        return [Label("[CORE] Success!")]

    def on_gather_assassin_pseudonym_pairs(self, e: Optional[Event]) -> List[HTMLComponent]:
        def pseudonym_list_factory(identifier: str, defaults: Dict[str, int]) -> List[HTMLComponent]:
            assassin = ASSASSINS_DATABASE.get(identifier)
            choices = [(c, i) for i, c in enumerate(assassin.pseudonyms) if c]  # hide any null (i.e. deleted) pseudonyms
            if len(choices) != 1:
                return [InputWithDropDown(
                    identifier="pseudonym",
                    title=f"{identifier}: Choose pseudonym",
                    options=choices,
                    selected=defaults.get(identifier, "")
                )]
            else:
                return [HiddenTextbox(
                    identifier="pseudonym",
                    default=choices[0][1]
                )]

        defaults = e.assassins if e is not None else {}
        # include hidden assassins if they are already in the event,
        # so that the umpire doesn't accidentally remove them from the event
        assassins = ASSASSINS_DATABASE.get_identifiers(include_hidden=lambda a: a.identifier in defaults)

        return [ForEach(
            identifier="assassin_selection",
            title="Choose which assassins are in this event",
            options=assassins,
            defaults=defaults,
            subcomponents_factory=pseudonym_list_factory
        )]

    def on_event_request_create(self, assassin_pseudonyms: Dict[str, int]) -> List[HTMLComponent]:
        def report_entry_factory(identifier: str, _) -> List[HTMLComponent]:
            pseudonym_id = assassin_pseudonyms[identifier]
            return [
                LargeTextEntry(
                    identifier=str(pseudonym_id),
                    title=f"Report: {identifier}",
                )
            ]

        assassins = list(assassin_pseudonyms.keys())
        potential_kills = []
        for a1 in assassins:
            for a2 in assassins:
                if a1 != a2:
                    potential_kills.append(
                        (f"{a1} kills {a2}", (a1, a2))
                    )

        html = [
            SelectorList(
                identifier=self.event_html_ids["Kills"],
                title="Select kills",
                options=potential_kills
            ),
            ForEach(
                identifier=self.event_html_ids["Reports"],
                title="Reports (select players with reports)",
                options=assassins,
                subcomponents_factory=report_entry_factory,
                explanation=[
                    "FORMATTING ADVICE",
                    "    [PX] Renders pseudonym of assassin with ID X (if in the event)",
                    "    [PX_i] Renders the ith pseudonym (with 0 as first pseudonym) of assassin with ID X (if in the event)",
                    "    [DX] Renders ALL pseudonyms of assassin with ID X (if in the event)",
                    "    [NX] Renders real name of assassin with ID X (if in the event)",
                    "ASSASSIN IDENTIFIERS"
                ] + [
                    f"    ({a._secret_id}) {a.real_name}"
                    for a in (ASSASSINS_DATABASE.get(a_id) for a_id in assassin_pseudonyms.keys())
                ],
                skippable_explanation=False
            ),
            HiddenJSON(self.event_html_ids["Assassin Pseudonym"], assassin_pseudonyms),
            DatetimeEntry(self.event_html_ids["Datetime"], "Enter date/time of event"),
            LargeTextEntry(self.event_html_ids["Headline"], "Headline"),
        ]
        return html

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        # process the response of the report entry component:
        # it returns a dict mapping assassin identifiers to dicts mapping (stringified) pseudonym ids to reports,
        # whereas the database has reports stored as a list of tuples (assassin identifier, pseudonym index, report)
        reports: List[Tuple[str, int, str]] = []
        for a_id, p_to_r in htmlResponse[self.event_html_ids["Reports"]].items():
            for p_index_str, r in p_to_r.items():
                reports.append(
                    (a_id, int(p_index_str), r)
                )
        e.reports = reports

        return [Label("[CORE] Success!")]

    def on_event_request_update(self, e: Event, assassin_pseudonyms: Dict[str, int]):
        def report_entry_factory(identifier: str, defaults: Dict[str, Dict[str, str]]) -> List[HTMLComponent]:
            pseudonym_id = str(assassin_pseudonyms[identifier])
            return [
                LargeTextEntry(
                    identifier=pseudonym_id,
                    title=f"Report: {identifier}",
                    default=defaults.get(identifier, {}).get(pseudonym_id, '')
                )
            ]

        assassins = list(assassin_pseudonyms.keys())
        potential_kills = []
        default_kills = []
        for a1 in assassins:
            for a2 in assassins:
                if a1 != a2:
                    kill_option = (f"{a1} kills {a2}", (a1, a2))
                    potential_kills.append(kill_option)
                    if (a1, a2) in e.kills:
                        default_kills.append(kill_option)

        # Convert the format of existing reports into a dict, for use by `report_entry_factory`.
        # Note that this will overwrite multiple reports attributed to the same player,
        # and also will not recognise reports attributed to a different pseudonym.
        # (This is the same behaviour as `AssassinDependentReportEntry` had.
        # It is ok at the moment because we don't support multiple reports in the frontend,
        # but the change of pseudonym issue could be annoying.)
        report_defaults: Dict[str, Dict[str, str]] = {}
        for t in e.reports:
            report_defaults.setdefault(t[0], {})[str(t[1])] = t[2]

        html = [
            HiddenTextbox(self.HTML_SECRET_ID, e.identifier),
            ForEach(
                identifier=self.event_html_ids["Reports"],
                title="Reports (select players with reports)",
                options=assassins,
                subcomponents_factory=report_entry_factory,
                explanation=[
                                "FORMATTING ADVICE",
                                "    [PX] Renders pseudonym of assassin with ID X (if in the event)",
                                "    [PX_i] Renders the ith pseudonym (with 0 as first pseudonym) of assassin with ID X (if in the event)",
                                "    [DX] Renders ALL pseudonyms of assassin with ID X (if in the event)",
                                "    [NX] Renders real name of assassin with ID X (if in the event)",
                                "ASSASSIN IDENTIFIERS"
                            ] + [
                                f"    ({a._secret_id}) {a.real_name}"
                                for a in (ASSASSINS_DATABASE.get(a_id) for a_id in assassin_pseudonyms.keys())
                            ],
                defaults=report_defaults
            ),
            SelectorList(
                identifier=self.event_html_ids["Kills"],
                title="Select kills",
                options=potential_kills,
                defaults=default_kills
            ),
            HiddenJSON(self.event_html_ids["Assassin Pseudonym"], assassin_pseudonyms),
            DatetimeEntry(self.event_html_ids["Datetime"], "Enter date/time of event", e.datetime),
            LargeTextEntry(self.event_html_ids["Headline"], "Headline", e.headline),
        ]
        return html

    def on_event_update(self, event: Event, htmlResponse: Dict) -> List[HTMLComponent]:
        event.assassins = htmlResponse[self.event_html_ids["Assassin Pseudonym"]]
        event.datetime = htmlResponse[self.event_html_ids["Datetime"]]
        event.headline = htmlResponse[self.event_html_ids["Headline"]]
        event.kills = htmlResponse[self.event_html_ids["Kills"]]
        # process the response of the report entry component:
        # it returns a dict mapping assassin identifiers to dicts mapping (stringified) pseudonym ids to reports,
        # whereas the database has reports stored as a list of tuples (assassin identifier, pseudonym index, report)
        reports: List[Tuple[str, int, str]] = []
        for a_id, p_to_r in htmlResponse[self.event_html_ids["Reports"]].items():
            for p_index_str, r in p_to_r.items():
                reports.append(
                    (a_id, int(p_index_str), r)
                )
        event.reports = reports

        return [Label("[CORE] Success!")]

    def on_event_request_delete(self, e: Event) -> List[HTMLComponent]:
        return [HiddenTextbox(self.HTML_SECRET_ID, e.identifier)]

    def on_event_delete(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return [Label("[CORE] Delete acknowledged.")]

    def on_request_hook_respond(self, hook: str) -> List[HTMLComponent]:
        if hook == self.hooks["hide_assassins"]:
            assassins = ASSASSINS_DATABASE.get_identifiers(include_hidden=lambda x: True)
            hidden_assassins = ASSASSINS_DATABASE.get_identifiers(include=lambda x: False, include_hidden=lambda x: True)
            components = [SelectorList(identifier=self.html_ids["Hidden Assassins"],
                                       title="Select assassins to hide",
                                       options=assassins,
                                       defaults=hidden_assassins)]
            return components
        return []

    def on_hook_respond(self, hook: str, html_response_args: Dict[str, Any], data: Any) -> List[HTMLComponent]:
        if hook == self.hooks["hide_assassins"]:
            assassins_to_hide = html_response_args[self.html_ids["Hidden Assassins"]]
            for a in ASSASSINS_DATABASE.get_filtered(include_hidden=lambda x: True):
                a.hidden = a.identifier in assassins_to_hide
            return_components = [Label("[Core] Set assassins' visibilities")]
            return return_components
        return []

    def get_all_exports(self, include_suppressed: bool = False) -> List[Export]:
        """
        Returns all exports from all plugins, including prepared hooked exports, sorted by display name
        """
        exports = []
        for p in PLUGINS:
            exports += p.exports

        for p in PLUGINS:
            for hooked_export in p.hooked_exports:

                # hideous disgusting lambda scoping rules means we have to do awful
                # terrible no good very bad shenanigans to get the lambdas to correctly
                # bind the values. ew!
                exports.append(
                    Export(
                        "core_plugin_hook_" + hooked_export.identifier,
                        hooked_export.display_name,
                        lambda export_identifier=hooked_export.identifier: self.ask_custom_hook(export_identifier),
                        lambda htmlResponse,
                               identifier=p.identifier,
                               export_identifier=hooked_export.identifier,
                               producer_function=hooked_export.producer,
                               call_first=hooked_export.call_first:
                            self.answer_custom_hook(
                                export_identifier,
                                htmlResponse,
                                data=producer_function(htmlResponse),
                                call_first=call_first,
                                hook_owner=identifier
                            )
                    )
                )

        suppressed_exports = GENERIC_STATE_DATABASE.arb_state.get("CorePlugin", {}).get("suppressed_exports", [])
        exports = [e for e in exports if include_suppressed or e.identifier not in suppressed_exports]
        export_priorities = GENERIC_STATE_DATABASE.arb_state.get("CorePlugin", {}).get("export_priorities", {})
        exports.sort(key=lambda e: (-export_priorities.get(e.identifier, 0), e.display_name))
        return exports

    def ask_suppress_exports(self):
        export_name_id_pairs = [(export.display_name, export.identifier)
                                for export in self.get_all_exports(include_suppressed=True)
                                if export.identifier not in self.IRREMOVABLE_EXPORTS]
        default_suppression = GENERIC_STATE_DATABASE.arb_state.get("CorePlugin", {}).get("suppressed_exports", [])
        return [
            SelectorList(
                identifier=self.config_html_ids["Suppressed Exports"],
                title="Choose the menu options that should not be displayed",
                defaults=default_suppression,
                options=export_name_id_pairs
            )
        ]

    def answer_suppress_exports(self, htmlResponse):
        new_suppressed_exports = set(htmlResponse[self.config_html_ids["Suppressed Exports"]])
        current_suppression = set(GENERIC_STATE_DATABASE.arb_state.get("CorePlugin", {}).get("suppressed_exports", []))
        # only update suppression for exports of loaded plugins
        for exp in self.get_all_exports(include_suppressed=True):
            exp_id = exp.identifier
            if exp_id in new_suppressed_exports:
                current_suppression.add(exp_id)
            else:
                current_suppression.discard(exp_id)

        # should be necessary since
        for exp_id in self.IRREMOVABLE_EXPORTS:
            current_suppression.discard(exp_id)

        GENERIC_STATE_DATABASE.arb_state.setdefault("CorePlugin", {})["suppressed_exports"] = list(current_suppression)
        return [Label("[CORE] Success!")]

    def ask_reorder_exports(self) -> List[HTMLComponent]:
        """
        Config option to re-order how Exports are displayed in the main menu.
        Currently it is only possible to 'pin' certain exports, but this is purely a frontend issue:
        each export is assigned a different "priority" value and they are sorted based on this.
        With the current 'pinning' interface, these take values 0 and 1 only.
        """
        export_name_id_pairs = [(export.display_name, export.identifier) for export in self.get_all_exports()]
        default_priorities = GENERIC_STATE_DATABASE.arb_state.get("CorePlugin", {}).get("export_priorities", {})
        default_pinned = [export_id for export_id, priority in default_priorities.items() if priority > 0]
        return [
            SelectorList(
                identifier=self.config_html_ids["Pinned Exports"],
                title="Choose menu items to pin to the top of the main menu",
                defaults=default_pinned,
                options=export_name_id_pairs
            )
        ]

    def answer_reorder_exports(self, htmlResponse: dict[str, Any]) -> List[HTMLComponent]:
        pinned_exports = set(htmlResponse[self.config_html_ids["Pinned Exports"]])
        # leave any hidden/unloaded exports' priorities intact,
        # and keep any priorities that are not 0 or 1 intact if they prioritise the correct exports
        # (this is for forwards-compatibility)
        current_priorities = GENERIC_STATE_DATABASE.arb_state.setdefault("CorePlugin", {}).setdefault("export_priorities", {})
        for e in self.get_all_exports():
            old_prio = current_priorities.get(e.identifier, 0)
            if e.identifier not in pinned_exports and old_prio > 0:
                current_priorities[e.identifier] = 0
            elif e.identifier in pinned_exports and old_prio <= 0:
                current_priorities[e.identifier] = 1
        return [Label("[CORE] Success!")]

    def ask_core_plugin_create_assassin(self):
        components = []
        for p in PLUGINS:
            components += p.on_assassin_request_create()
        return components

    def answer_core_plugin_create_assassin(self, html_response_args: Dict):
        params = {}
        for p in self.params:
            params[self.params[p]] = html_response_args[p]
        params["pseudonyms"] = [params["pseudonyms"]]
        assassin = Assassin(**params)
        return_components = []
        for p in PLUGINS:
            return_components += p.on_assassin_create(assassin, html_response_args)
        ASSASSINS_DATABASE.add(assassin)
        return return_components

    def ask_core_plugin_update_assassin(self, arg: str):
        assassin = ASSASSINS_DATABASE.get(arg)
        components = []
        for p in PLUGINS:
            components += p.on_assassin_request_update(assassin)
        return components

    def answer_core_plugin_update_assassin(self, html_response_args: Dict):
        ident = html_response_args[self.HTML_SECRET_ID]
        assassin = ASSASSINS_DATABASE.get(ident)
        return_components = []
        for p in PLUGINS:
            return_components += p.on_assassin_update(assassin, html_response_args)
        return return_components

    def gather_assassin_pseudonym_pairs(self, e_id: Optional[str] = None) -> HTMLComponent:
        """
        One of the `options_functions` of Event -> Create and Event-> Update.
        The point of this is to return the assassin-pseudonym selector.
        It is an API call to allow UIConfigPlugin's UI overrides to work here.
        """
        e = EVENTS_DATABASE.get(e_id) if e_id is not None else None
        components = []
        for p in PLUGINS:
            components += p.on_gather_assassin_pseudonym_pairs(e)
        return components

    def ask_core_plugin_create_event(self, assassin_selection: Dict[str, Dict[str, int]]) -> List[HTMLComponent]:
        # each value of `assassin_selection` is a dict with a single key "pseudonym"
        # so convert this into a direct mapping
        assassin_pseudonyms = {a_id: info["pseudonym"] for a_id, info in assassin_selection.items()}
        components = []
        for p in PLUGINS:
            components += p.on_event_request_create(assassin_pseudonyms)
        return components

    def answer_core_plugin_create_event(self, html_response_args: Dict) -> List[HTMLComponent]:
        params = {}
        for p in self.event_params:
            params[self.event_params[p]] = html_response_args[p]
        event = Event(**params)
        return_components = []
        for p in PLUGINS:
            return_components += p.on_event_create(event, html_response_args)
        EVENTS_DATABASE.add(event)

        print(event)
        return return_components

    def ask_core_plugin_update_event(self, event_id: str, assassin_selection: Dict[str, Dict[str, int]]) -> List[HTMLComponent]:
        event = EVENTS_DATABASE.get(event_id)
        # each value of `assassin_selection` is a dict with a single key "pseudonym"
        # so convert this into a direct mapping
        assassin_pseudonyms = {a_id: info["pseudonym"] for a_id, info in assassin_selection.items()}
        components = []
        for p in PLUGINS:
            components += p.on_event_request_update(event, assassin_pseudonyms)
        return components

    def answer_core_plugin_update_event(self, html_response_args: Dict) -> List[HTMLComponent]:
        ident = html_response_args[self.HTML_SECRET_ID]
        event = EVENTS_DATABASE.get(ident)
        event.pluginState["sanity_checks"] = []
        components = []
        for p in PLUGINS:
            components += p.on_event_update(event, html_response_args)
        return components

    def gather_events(self) -> List[Tuple[str, str]]:
        # headline is truncated because `inquirer` doesn't deal with overlong options well
        return [
                (f"[{event.datetime.strftime('%Y-%m-%d %H:%M %p')}] {event.headline[0:25].rstrip()}", identifier)
                for identifier, event in sorted(EVENTS_DATABASE.events.items(), key=lambda x: x[1].datetime, reverse=True)
        ]

    def ask_core_plugin_delete_event(self, event_id: str):
        event = EVENTS_DATABASE.get(event_id)
        components = []
        for p in PLUGINS:
            components += p.on_event_request_delete(event)
        return components

    def answer_core_plugin_delete_event(self, html_response_args: Dict):
        ident = html_response_args[self.HTML_SECRET_ID]
        event = EVENTS_DATABASE.get(ident)
        components = []
        for p in PLUGINS:
            components += p.on_event_delete(event, html_response_args)
        del EVENTS_DATABASE.events[ident]
        return components

    def ask_core_plugin_update_config(self):
        plugins = [p for p in GENERIC_STATE_DATABASE.plugin_map]
        plugins.remove("CorePlugin")
        return [
            SelectorList(
                self.identifier + "_config",
                title="Enable or disable plugins",
                options=sorted(plugins),
                defaults=[p for p in plugins if GENERIC_STATE_DATABASE.plugin_map[p]]
            )
        ]

    def ask_generate_pages(self):
        components = []
        event_count = 0
        for e in EVENTS_DATABASE.events.values():
            must_check = False
            sanity_check_count = 0
            explanations = []
            for sanity_check_identifier, sanity_check in SANITY_CHECKS.items():
                if sanity_check.has_marked(e):
                    continue
                changes = sanity_check.suggest_event_fixes(e)
                if not changes:
                    continue
                if not must_check:
                    must_check = True
                    components.append(
                        HiddenTextbox(
                            identifier=f"SanityCheck_{event_count}",
                            default=e.identifier
                        )
                    )

                components.append(
                    HiddenTextbox(
                        identifier=f"SanityCheck_{event_count}_{sanity_check_count}",
                        default=sanity_check_identifier
                    )
                )

                for i, suggestion in enumerate(changes):
                    components.append(
                        HiddenTextbox(
                            identifier=f"SanityCheck_{event_count}_{sanity_check_count}_{i}_identifier",
                            default=suggestion.identifier
                        )
                    )
                    components.append(
                        HiddenTextbox(
                            identifier=f"SanityCheck_{event_count}_{sanity_check_count}_{i}_explanation",
                            default=suggestion.explanation
                        )
                    )
                    explanations.append(suggestion.explanation)

                sanity_check_count += 1

            if explanations:
                components.append(
                    SelectorList(
                        identifier=f"SanityCheck_{event_count}_explanations",
                        title=f"[SANITY CHECK] {e.identifier}",
                        options=explanations,
                        defaults=explanations
                    )
                )
            if must_check:
                event_count += 1

        if components:
            components.insert(0, Label("[SANITY CHECK] Potential errors detected. Select changes to make."))

        for p in PLUGINS:
            components += p.on_page_request_generate()
        return components

    def answer_generate_pages(self, html_response_args: Dict):

        components = []

        events_count = 0
        while f"SanityCheck_{events_count}" in html_response_args:
            event_id = html_response_args[f"SanityCheck_{events_count}"]
            for sanity_check in SANITY_CHECKS.values():
                sanity_check.mark(EVENTS_DATABASE.events[event_id])
            sanity_check_count = 0
            selected_changes = html_response_args[f"SanityCheck_{events_count}_explanations"]
            while f"SanityCheck_{events_count}_{sanity_check_count}" in html_response_args:
                sanity_check_str = f"SanityCheck_{events_count}_{sanity_check_count}"
                sanity_check_id = html_response_args[sanity_check_str]
                suggestion_count = 0
                requested_ids = []
                while f"{sanity_check_str}_{suggestion_count}_identifier" in html_response_args:
                    base = f"{sanity_check_str}_{suggestion_count}"
                    suggestion_id = html_response_args[f"{base}_identifier"]
                    explanation = html_response_args[f"{base}_explanation"]
                    if explanation in selected_changes:
                        requested_ids.append(suggestion_id)
                    suggestion_count += 1
                if requested_ids:
                    components += SANITY_CHECKS[sanity_check_id].fix_event(
                        EVENTS_DATABASE.events[event_id],
                        requested_ids
                    )
                sanity_check_count += 1
            events_count += 1

        for p in PLUGINS:
            components += p.on_page_generate(html_response_args)
        return components

    def answer_core_plugin_update_config(self, htmlResponse):
        enabled_plugins = htmlResponse[self.identifier + "_config"]
        enabled_plugins.append("CorePlugin")
        for p in GENERIC_STATE_DATABASE.plugin_map:
            GENERIC_STATE_DATABASE.plugin_map[p] = (p in enabled_plugins)
        return [
            Label("[CORE] Plugin change success!")
        ]

    def ask_custom_hook(self, hook: str) -> List[HTMLComponent]:
        """
        Allows Plugins to expose global hooks
        """
        components = []
        for p in PLUGINS:
            components += p.on_request_hook_respond(hook)
        return components

    def answer_custom_hook(self, hook: str, htmlResponse, data, call_first: bool, hook_owner: str) -> List[HTMLComponent]:
        """
        Allows Plugins to expose global hooks
        """
        components = []

        if call_first:
            components += PLUGINS.plugins[hook_owner].on_hook_respond(hook, htmlResponse, data)

        for p in PLUGINS:
            if p.identifier == hook_owner:
                continue
            components += p.on_hook_respond(hook, htmlResponse, data)

        if not call_first:
            components += PLUGINS.plugins[hook_owner].on_hook_respond(hook, htmlResponse, data)

        return components

    def gather_config_options(self) -> ConfigOptionsList:
        """
        Gathers the name of all ConfigExports from all plugins, and returns a ConfigOptionsList
        """
        config_options = [c for p in PLUGINS for c in p.config_exports]
        config_options.sort(key=lambda c: c.display_name)
        return ConfigOptionsList(identifier="config_option",
                                 title="",
                                 config_options=config_options)

    def ask_config(self, config_option: ConfigExport):
        """
        Opens the menu for a chosen config option
        """
        if isinstance(config_option, ConfigExport):
            return [
                HiddenTextbox(
                    identifier=self.identifier + "_config",
                    default=config_option.identifier
                )
            ] + config_option.ask()
        else:
            return [
                HiddenTextbox(
                    identifier=self.identifier + "_config",
                    default=""
                )
            ]

    def answer_config(self, htmlResponse):
        all_config_exports = []
        for p in PLUGINS:
            all_config_exports += p.config_exports

        config_identifier = htmlResponse[self.identifier + "_config"]

        config: ConfigExport
        for c in all_config_exports:
            if c.identifier == config_identifier:
                config = c
                break
        else:
            return []

        return config.answer(htmlResponse)

    def ask_set_game_start(self):
        return [
            DatetimeEntry(
                self.identifier + "_game_start",
                title="Enter game start",
                default=get_game_start()
            )
        ]

    def answer_set_game_start(self, htmlResponse):
        set_game_start(htmlResponse[self.identifier + "_game_start"])
        return [
            Label(f"[CORE] Set game start to {get_game_start().strftime('%Y-%m-%d %H:%M:%S')}")
        ]
