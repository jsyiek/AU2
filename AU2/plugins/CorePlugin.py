import glob
import os.path

from typing import Dict, List

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Assassin, Event
from AU2.html_components import HTMLComponent
from AU2.html_components.ArbitraryList import ArbitraryList
from AU2.html_components.AssassinDependentReportEntry import AssassinDependentReportEntry
from AU2.html_components.AssassinPseudonymPair import AssassinPseudonymPair
from AU2.html_components.Checkbox import Checkbox
from AU2.html_components.DatetimeEntry import DatetimeEntry
from AU2.html_components.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.Dependency import Dependency
from AU2.html_components.HiddenTextbox import HiddenTextbox
from AU2.html_components.InputWithDropDown import InputWithDropDown
from AU2.html_components.AssassinDependentKillEntry import AssassinDependentKillEntry
from AU2.html_components.Label import Label
from AU2.html_components.LargeTextEntry import LargeTextEntry
from AU2.html_components.NamedSmallTextbox import NamedSmallTextbox
from AU2.html_components.SelectorList import SelectorList
from AU2.plugins import CUSTOM_PLUGINS_DIR
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export, ConfigExport
from AU2.plugins.AvailablePlugins import __PluginMap
from AU2.plugins.constants import COLLEGES, WATER_STATUSES
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

        self.html_ids_list = [
            "Pseudonym",
            "Real Name",
            "Pronouns"
            "Email",
            "Address",
            "Water Status",
            "College",
            "Notes",
            "Police"
        ]

        self.html_ids = {
            "Pseudonym": self.identifier + "_pseudonym",
            "Real Name": self.identifier + "_real_name",
            "Pronouns": self.identifier + "_pronouns",
            "Email": self.identifier + "_email",
            "Address": self.identifier + "_address",
            "Water Status": self.identifier + "_water_status",
            "College": self.identifier + "_college",
            "Notes": self.identifier + "_notes",
            "Police": self.identifier + "_police"
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
            self.event_html_ids["Reports"]: "reports",
            self.event_html_ids["Kills"]: "kills"
        }

        self.config_html_ids = {
            "Suppressed Exports": self.identifier + "_suppressed_exports"
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
                (lambda: sorted([v for v in ASSASSINS_DATABASE.assassins], key=lambda n: n.lower()),)
            ),
            Export(
                "core_event_create_event",
                "Event -> Create",
                self.ask_core_plugin_create_event,
                self.answer_core_plugin_create_event
            ),
            Export(
                "core_event_delete_event",
                "Event -> Delete",
                self.ask_core_plugin_delete_event,
                self.answer_core_plugin_delete_event,
                (lambda: [v for v in EVENTS_DATABASE.events],)
            ),
            Export(
                "core_event_update_event",
                "Event -> Update",
                self.ask_core_plugin_update_event,
                self.answer_core_plugin_update_event,
                (lambda: [v for v in EVENTS_DATABASE.events],)
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
                (self.gather_config_names,)
            )
        ]

        # str -> HookedExport
        self.hooks = {}

        self.config_exports = [
            ConfigExport(
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

    def on_assassin_request_update(self, assassin):
        html = [
            HiddenTextbox(self.HTML_SECRET_ID, assassin.identifier),
            ArbitraryList(self.html_ids["Pseudonym"], "Pseudonyms", assassin.pseudonyms),
            DefaultNamedSmallTextbox(self.html_ids["Real Name"], "Real Name", assassin.real_name),
            DefaultNamedSmallTextbox(self.html_ids["Pronouns"], "Pronouns", assassin.pronouns),
            DefaultNamedSmallTextbox(self.html_ids["Email"], "Email", assassin.email, type_="email"),
            DefaultNamedSmallTextbox(self.html_ids["Address"], "Address", assassin.address),
            InputWithDropDown(self.html_ids["Water Status"], "Water Status", WATER_STATUSES, selected=assassin.water_status),
            InputWithDropDown(self.html_ids["College"], "College", COLLEGES, selected=assassin.college),
            LargeTextEntry(self.html_ids["Notes"], "Notes", default=assassin.notes),
            Checkbox(self.html_ids["Police"], "Police? (y/n)", checked=assassin.is_police)
        ]
        return html

    def on_assassin_update(self, assassin: Assassin, htmlResponse: Dict) -> List[HTMLComponent]:
        assassin.pseudonyms = htmlResponse[self.html_ids["Pseudonym"]]
        assassin.real_name = htmlResponse[self.html_ids["Real Name"]]
        assassin.pronouns = htmlResponse[self.html_ids["Pronouns"]]
        assassin.address = htmlResponse[self.html_ids["Address"]]
        assassin.college = htmlResponse[self.html_ids["College"]]
        assassin.notes = htmlResponse[self.html_ids["Notes"]]
        assassin.is_police = htmlResponse[self.html_ids["Police"]]
        return [Label("[CORE] Success!")]

    def on_event_request_create(self):
        assassins = [(a.identifier, a.pseudonyms) for a in ASSASSINS_DATABASE.assassins.values()]
        html = [
            Dependency(
                dependentOn=self.event_html_ids["Assassin Pseudonym"],
                htmlComponents=[
                    AssassinPseudonymPair(self.event_html_ids["Assassin Pseudonym"], "Assassin Pseudonym Selection", assassins),
                    AssassinDependentReportEntry(self.event_html_ids["Assassin Pseudonym"], self.event_html_ids["Reports"], "Reports"),
                    AssassinDependentKillEntry(self.event_html_ids["Assassin Pseudonym"], self.event_html_ids["Kills"], "Kills")
                ]
            ),
            DatetimeEntry(self.event_html_ids["Datetime"], "Enter date/time of event"),
            LargeTextEntry(self.event_html_ids["Headline"], "Headline"),
        ]
        return html

    def on_event_create(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return [Label("[CORE] Success!")]

    def on_event_request_update(self, e: Event):
        assassins = [(a.identifier, a.pseudonyms) for a in ASSASSINS_DATABASE.assassins.values()]
        html = [
            HiddenTextbox(self.HTML_SECRET_ID, e.identifier),
            Dependency(
                dependentOn=self.event_html_ids["Assassin Pseudonym"],
                htmlComponents=[
                    AssassinPseudonymPair(self.event_html_ids["Assassin Pseudonym"], "Assassin Pseudonym Selection", assassins, e.assassins),
                    AssassinDependentReportEntry(self.event_html_ids["Assassin Pseudonym"], self.event_html_ids["Reports"], "Reports", e.reports),
                    AssassinDependentKillEntry(self.event_html_ids["Assassin Pseudonym"], self.event_html_ids["Kills"], "Kills", e.kills)
                ]
            ),
            DatetimeEntry(self.event_html_ids["Datetime"], "Enter date/time of event", e.datetime),
            LargeTextEntry(self.event_html_ids["Headline"], "Headline", e.headline),
        ]
        return html

    def on_event_update(self, event: Event, htmlResponse: Dict) -> List[HTMLComponent]:
        event.assassins = htmlResponse[self.event_html_ids["Assassin Pseudonym"]]
        event.datetime = htmlResponse[self.event_html_ids["Datetime"]]
        event.headline = htmlResponse[self.event_html_ids["Headline"]]
        event.reports = htmlResponse[self.event_html_ids["Reports"]]
        event.kills = htmlResponse[self.event_html_ids["Kills"]]
        return [Label("[CORE] Success!")]

    def on_event_request_delete(self, e: Event) -> List[HTMLComponent]:
        return [HiddenTextbox(self.HTML_SECRET_ID, e.identifier)]

    def on_event_delete(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return [Label("[CORE] Delete acknowledged.")]

    def get_all_exports(self) -> List[Export]:
        """
        Returns all exports from all plugins, including prepared hooked exports
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
        exports = [e for e in exports if e.identifier not in suppressed_exports]
        return exports

    def ask_suppress_exports(self):
        export_identifiers = [export.identifier for export in self.get_all_exports()]
        default_suppression = GENERIC_STATE_DATABASE.arb_state.get("CorePlugin", {}).get("suppressed_exports", [])
        export_identifiers = sorted(list(set(export_identifiers + default_suppression)))
        for exp in self.IRREMOVABLE_EXPORTS:
            if exp in export_identifiers:
                export_identifiers.remove(exp)
        return [
            SelectorList(
                identifier=self.config_html_ids["Suppressed Exports"],
                title="Choose the menu options that should not be displayed",
                defaults=default_suppression,
                options=export_identifiers
            )
        ]

    def answer_suppress_exports(self, htmlResponse):
        suppressed_exports = htmlResponse[self.config_html_ids["Suppressed Exports"]]
        for exp in self.IRREMOVABLE_EXPORTS:
            if exp in suppressed_exports:
                suppressed_exports.remove(exp)
        GENERIC_STATE_DATABASE.arb_state.setdefault("CorePlugin", {})["suppressed_exports"] = suppressed_exports
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
        assassin = ASSASSINS_DATABASE.assassins[arg]
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

    def ask_core_plugin_create_event(self):
        components = []
        for p in PLUGINS:
            components += p.on_event_request_create()
        return components

    def answer_core_plugin_create_event(self, html_response_args: Dict):
        params = {}
        for p in self.event_params:
            params[self.event_params[p]] = html_response_args[p]
        event = Event(**params)
        return_components = []
        for p in PLUGINS:
            return_components += p.on_event_create(event, html_response_args)
        EVENTS_DATABASE.add(event)
        return return_components

    def ask_core_plugin_update_event(self, event_id: str):
        event = EVENTS_DATABASE.get(event_id)
        components = []
        for p in PLUGINS:
            components += p.on_event_request_update(event)
        return components

    def answer_core_plugin_update_event(self, html_response_args: Dict):
        ident = html_response_args[self.HTML_SECRET_ID]
        event = EVENTS_DATABASE.get(ident)
        components = []
        for p in PLUGINS:
            components += p.on_event_update(event, html_response_args)
        return components

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
                options=plugins,
                defaults=[p for p in plugins if GENERIC_STATE_DATABASE.plugin_map[p]]
            )
        ]

    def ask_generate_pages(self):
        components = []
        for p in PLUGINS:
            components += p.on_page_request_generate()
        return components

    def answer_generate_pages(self, html_response_args: Dict):
        components = []
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
            PLUGINS.plugins[hook_owner].on_hook_respond(hook, htmlResponse, data)

        for p in PLUGINS:
            if p.identifier == hook_owner:
                continue
            components += p.on_hook_respond(hook, htmlResponse, data)

        if not call_first:
            PLUGINS.plugins[hook_owner].on_hook_respond(hook, htmlResponse, data)

        return components

    def gather_config_names(self):
        """
        Gathers the name of all ConfigExports from all plugins
        """
        names = []
        for p in PLUGINS:
            for c in p.config_exports:
                names.append(c.display_name)
        names.sort()
        return names

    def ask_config(self, config_option: str):
        """
        Opens the menu for a chosen config option
        """
        all_config_exports = []
        for p in PLUGINS:
            all_config_exports += p.config_exports

        config: ConfigExport
        for c in all_config_exports:
            if c.display_name == config_option:
                config = c
                break
        else:
            return [
                HiddenTextbox(
                    identifier=self.identifier + "_config",
                    default=""
                )
            ]

        return [
            HiddenTextbox(
                identifier=self.identifier + "_config",
                default=config.identifier
            )
        ] + config.ask()

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
