import glob
import os.path

from typing import Any, Callable, Dict, List, Optional, Tuple

from AU2 import BASE_WRITE_LOCATION
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Assassin, Event
from AU2.database.model.database_utils import refresh_databases
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.Table import Table
from AU2.html_components.SpecialComponents.EditablePseudonymList import EditablePseudonymList, PseudonymData
from AU2.html_components.SpecialComponents.ConfigOptionsList import ConfigOptionsList
from AU2.html_components.DependentComponents.AssassinDependentReportEntry import AssassinDependentReportEntry
from AU2.html_components.DependentComponents.AssassinPseudonymPair import AssassinPseudonymPair
from AU2.html_components.DerivativeComponents.DigitsChallenge import DigitsChallenge, verify_DigitsChallenge
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.DatetimeEntry import DatetimeEntry
from AU2.html_components.SimpleComponents.OptionalDatetimeEntry import OptionalDatetimeEntry
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.MetaComponents.Dependency import Dependency
from AU2.html_components.SimpleComponents.HiddenJSON import HiddenJSON
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown
from AU2.html_components.DependentComponents.AssassinDependentKillEntry import AssassinDependentKillEntry
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.LargeTextEntry import LargeTextEntry
from AU2.html_components.SimpleComponents.NamedSmallTextbox import NamedSmallTextbox
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.plugins import CUSTOM_PLUGINS_DIR
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export, ConfigExport, HookedExport, DangerousConfigExport, \
    AttributePairTableRow
from AU2.plugins.AvailablePlugins import __PluginMap
from AU2.plugins.constants import COLLEGES, WATER_STATUSES
from AU2.plugins.sanity_checks import SANITY_CHECKS
from AU2.plugins.util.game import get_game_start, set_game_start, get_game_end, set_game_end
from AU2.plugins.util.date_utils import get_now_dt

AVAILABLE_PLUGINS = {}


def registered_plugin(plugin_class):
    plugin = plugin_class()
    AVAILABLE_PLUGINS[plugin.identifier] = plugin
    return plugin_class


PLUGINS = __PluginMap({})  # initialise first without any plugins to allow PLUGINS to be shared by other plugins

for file in glob.glob(os.path.join(CUSTOM_PLUGINS_DIR, "*.py")):
    name = os.path.splitext(os.path.basename(file))[0]
    module = __import__(f"AU2.plugins.custom_plugins.{name}")

PLUGINS.update(AVAILABLE_PLUGINS)  # actually enable plugins

# maps game types to default plugin settings for Setup Game
# plugins not explicitly mentioned are left as is,
# note that the bounty plugins will be dealt with separately
GAME_TYPE_PLUGIN_MAP = {
    "Standard Game": {
        "CompetencyPlugin": True,
        "LocalBackupPlugin": True,
        "MafiaPlugin": False,
        "MayWeekUtilitiesPlugin": False,
        "PageGeneratorPlugin": True,
        "PlayerImporterPlugin": True,
        "PolicePlugin": True,
        "RandomGamePlugin": False,
        "ScoringPlugin": True,
        "TargetingPlugin": True,
        "UIConfigPlugin": True,
        "WantedPlugin": True,
    },
    # Can't implement Setup Game for MayWeekUtilitiesPlugin at the moment because config options depend on whether
    # teams are enabled or not, and doing a partial implementation would mislead users.
    # "May Week": {
    #     "CompetencyPlugin":False,
    #     "LocalBackupPlugin": True,
    #     "MafiaPlugin": False,
    #     "MayWeekUtilitiesPlugin": True,
    #     "PageGeneratorPlugin": True,  # needed to be able to hide events
    #     "PolicePlugin": False,
    #     "RandomGamePlugin": False,
    #     "ScoringPlugin": False,
    #     "TargetingPlugin": False,
    #     "UIConfigPlugin": True,
    #     "WantedPlugin": True,
    # }
}


@registered_plugin
class CorePlugin(AbstractPlugin):

    PLUGIN_ENABLE_EXPORT: str = "core_plugin_config_update"
    CONFIG_PARAMETER_EXPORT: str = "core_plugin_edit_config"
    IRREMOVABLE_EXPORTS = [PLUGIN_ENABLE_EXPORT, CONFIG_PARAMETER_EXPORT]

    def __init__(self):
        super().__init__("CorePlugin")
        self.HTML_SECRET_ID = "CorePlugin_identifier"

        self.html_ids = {
            "Assassins": self.identifier + "_assassin",
            "Events": self.identifier + "_events",
            "Pseudonym": self.identifier + "_pseudonym",
            "Real Name": self.identifier + "_real_name",
            "Pronouns": self.identifier + "_pronouns",
            "Email": self.identifier + "_email",
            "Address": self.identifier + "_address",
            "Water Status": self.identifier + "_water_status",
            "College": self.identifier + "_college",
            "Notes": self.identifier + "_notes",
            "Police": self.identifier + "_police",
            "Hidden Assassins": self.identifier + "_hidden_assassins",
            "Nuke Database": self.identifier + "_nuke",
            "Secret Number": self.identifier + "_secret_confirm",
            "Delete Event": self.identifier + "_delete_event",
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
            "Suppressed Exports": self.identifier + "_suppressed_exports",
            "Pinned Exports": self.identifier + "_pinned_exports",
            "Plugins": self.identifier + "_plugins",
            "Setup Error": self.identifier + "_setup_error",
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
                "core_assassin_update_pseudonyms",
                "Assassin -> Pseudonyms",
                self.ask_core_plugin_update_pseudonyms,
                self.answer_core_plugin_update_pseudonyms,
                ((lambda: ASSASSINS_DATABASE.get_identifiers()),)
            ),
            Export(
                "core_assassin_summary",
                "Assassin -> Summary",
                self.ask_core_plugin_summary_assassin,
                self.answer_core_plugin_summary_assassin
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
                (self.gather_events,)
            ),
            Export(
                "core_event_status",
                "Event -> Summary",
                self.ask_core_plugin_summary_event,
                self.answer_core_plugin_summary_event
            ),
            Export(
                "core_event_update_event",
                "Event -> Update",
                self.ask_core_plugin_update_event,
                self.answer_core_plugin_update_event,
                (self.gather_events,)
            ),
            Export(
                "core_event_update_reports",
                "Event -> Reports",
                self.ask_core_plugin_update_reports,
                self.answer_core_plugin_update_reports,
                (self.gather_events,)
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
            ),
            Export(
                identifier="core_plugin_reset_database",
                display_name="Reset Database",
                ask=self.ask_reset_database,
                answer=self.answer_reset_database
            ),
            Export(
                identifier="core_plugin_setup_game",
                display_name="Setup Game",
                ask=self.ask_setup_game,
                answer=self.answer_setup_game,
                options_functions=(self.gather_game_types,)
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
                "core_plugin_set_game_end",
                "CorePlugin -> Set game end",
                self.ask_set_game_end,
                self.answer_set_game_end
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

    def render_assassin_summary(self, assassin: Assassin) -> List[AttributePairTableRow]:
        player_type = assassin.is_police and "Police" or "Player"
        hidden = assassin.hidden and "HIDDEN" or ""
        return [
            ("ID", str(assassin._secret_id)),
            ("Type", f"{hidden} {player_type}"),
            ("Name", assassin.real_name),
            *((f"Pseudonym {i} [P{assassin._secret_id}_{i}]", p)
                for i, p in enumerate(assassin.pseudonyms) if p),
            ("Pronouns", assassin.pronouns),
            ("Email", assassin.email),
            ("Address", assassin.address),
            ("Water status", assassin.water_status),
            ("College", assassin.college),
            ("Notes", assassin.notes)
        ]

    # CorePlugin can't be disabled
    def enabled(self) -> bool:
        return True

    def ask_core_plugin_summary_assassin(self):
        return [
            InputWithDropDown(
                self.html_ids["Assassins"],
                title="Select assassin to show status for",
                options=ASSASSINS_DATABASE.get_identifiers(include_hidden=lambda _: True))
        ] + sum((p.on_request_assassin_summary() for p in PLUGINS), start=[])

    def answer_core_plugin_summary_assassin(self, htmlResponse) -> List[HTMLComponent]:
        ident = htmlResponse[self.html_ids["Assassins"]]
        assassin = ASSASSINS_DATABASE.get(ident)
        return self._answer_rendering(assassin, lambda p, a: p.render_assassin_summary(a))

    def render_event_summary(self, event: Event) -> List[AttributePairTableRow]:
        response = [
            ("ID", str(event._Event__secret_id)),
            ("Headline", event.headline),
            ("Date/time", event.datetime),
            ("Deaths", ", ".join(kill[1] for kill in event.kills))
        ]

        snapshot = lambda a: f"{a.real_name} ({a._secret_id})"
        for (i, ident) in enumerate(event.assassins):
            a = ASSASSINS_DATABASE.get(ident)
            pseudonym = a.get_pseudonym(event.assassins[ident])
            response.append((f"Participant {i+1}", f"{snapshot(a)} as {pseudonym}"))

        for (i, (ident, pseudonym_idx, _)) in enumerate(event.reports):
            a = ASSASSINS_DATABASE.get(ident)
            pseudonym = a.get_pseudonym(pseudonym_idx)
            response.append((f"Report {i+1}", f"{snapshot(a)} as {pseudonym}"))

        for (i, (killer_id, victim_id)) in enumerate(event.kills):
            killer = ASSASSINS_DATABASE.get(killer_id)
            victim = ASSASSINS_DATABASE.get(victim_id)
            response.append((f"Kill {i+1}", f"{snapshot(killer)} kills {snapshot(victim)}"))
        return response

    def ask_core_plugin_summary_event(self) -> List[HTMLComponent]:
        return [
            InputWithDropDown(
                self.html_ids["Events"],
                title="Select events to show status for",
                options=self.gather_events()
            )
        ] + sum((p.on_request_event_summary() for p in PLUGINS), start=[])

    def answer_core_plugin_summary_event(self, htmlResponse) -> List[HTMLComponent]:
        ident = htmlResponse[self.html_ids["Events"]]
        event = EVENTS_DATABASE.get(ident)
        return self._answer_rendering(event, lambda p, e: p.render_event_summary(e))

    def _answer_rendering(self, obj: object, renderer: Callable[[AbstractPlugin, object], List[AttributePairTableRow]]) -> List[HTMLComponent]:
        results: List[Tuple[str, str]] = renderer(self, obj)
        for p in PLUGINS:
            if isinstance(p, CorePlugin):
                continue
            results += renderer(p, obj)
        headings = (
            "Attribute" + " "*25,
            "Value" + " "*80
        )
        return [Table(results, headings=headings)]

    def on_assassin_request_create(self):
        # use this to detect whether the game has started or not, since sending the first email is the point when
        # targets are "locked in" and adding new non-police players becomes dangerous
        last_emailed_event = int(
            GENERIC_STATE_DATABASE.arb_state.get("TargetingPlugin", {}).get("last_emailed_event", -1)
        )

        html = [
            NamedSmallTextbox(self.html_ids["Pseudonym"], "Initial Pseudonym"),
            NamedSmallTextbox(self.html_ids["Real Name"], "Real Name"),
            NamedSmallTextbox(self.html_ids["Pronouns"], "Pronouns"),
            NamedSmallTextbox(self.html_ids["Email"], "Email", type_="email"),
            NamedSmallTextbox(self.html_ids["Address"], "Address"),
            InputWithDropDown(self.html_ids["Water Status"], "Water Status", WATER_STATUSES),
            InputWithDropDown(self.html_ids["College"], "College", COLLEGES),
            LargeTextEntry(self.html_ids["Notes"], "Notes"),
            Checkbox(self.html_ids["Police"], "Police? (y/n)",
                     checked=last_emailed_event >= 0,
                     force_default=last_emailed_event >= 0)
        ]
        return html

    def on_assassin_create(self, assassin: Assassin, htmlResponse) -> List[HTMLComponent]:
        return [Label("[CORE] Success!")]

    def on_assassin_request_update(self, assassin: Assassin):
        # use this to detect whether the game has started or not, since sending the first email is the point when
        # targets are "locked in" and changing player types becomes dangerous.
        last_emailed_event = int(
            GENERIC_STATE_DATABASE.arb_state.get("TargetingPlugin", {}).get("last_emailed_event", -1)
        )
        html = [
            HiddenTextbox(self.HTML_SECRET_ID, assassin.identifier),
            *self.ask_core_plugin_update_pseudonyms(assassin.identifier),
            DefaultNamedSmallTextbox(self.html_ids["Real Name"], "Real Name", assassin.real_name),
            DefaultNamedSmallTextbox(self.html_ids["Pronouns"], "Pronouns", assassin.pronouns),
            DefaultNamedSmallTextbox(self.html_ids["Email"], "Email", assassin.email, type_="email"),
            DefaultNamedSmallTextbox(self.html_ids["Address"], "Address", assassin.address),
            InputWithDropDown(self.html_ids["Water Status"], "Water Status", WATER_STATUSES, selected=assassin.water_status),
            InputWithDropDown(self.html_ids["College"], "College", COLLEGES, selected=assassin.college),
            LargeTextEntry(self.html_ids["Notes"], "Notes", default=assassin.notes),
            Checkbox(self.html_ids["Police"], "Police? (y/n)",
                     checked=assassin.is_police,
                     force_default=last_emailed_event >= 0)
        ]
        return html

    def on_assassin_update(self, assassin: Assassin, htmlResponse: Dict) -> List[HTMLComponent]:
        self.answer_core_plugin_update_pseudonyms(htmlResponse)
        assassin.real_name = htmlResponse[self.html_ids["Real Name"]]
        assassin.pronouns = htmlResponse[self.html_ids["Pronouns"]]
        assassin.email = htmlResponse[self.html_ids["Email"]]
        assassin.address = htmlResponse[self.html_ids["Address"]]
        assassin.water_status = htmlResponse[self.html_ids["Water Status"]]
        assassin.college = htmlResponse[self.html_ids["College"]]
        assassin.notes = htmlResponse[self.html_ids["Notes"]]
        assassin.is_police = htmlResponse[self.html_ids["Police"]]
        return [Label("[CORE] Success!")]

    def on_event_request_create(self):
        assassins = ASSASSINS_DATABASE.get_ident_pseudonym_pairs()
        html = [
            Dependency(
                dependentOn=self.event_html_ids["Assassin Pseudonym"],
                htmlComponents=[
                    AssassinPseudonymPair(self.event_html_ids["Assassin Pseudonym"], "Assassin Pseudonym Selection", assassins),
                    *self.ask_core_plugin_update_reports(standalone=False),
                    Dependency(
                        dependentOn=self.event_html_ids["Kills"],
                        htmlComponents=[
                            AssassinDependentKillEntry(self.event_html_ids["Assassin Pseudonym"], self.event_html_ids["Kills"], "Kills")
                        ]
                    )
                ]
            ),
            DatetimeEntry(self.event_html_ids["Datetime"], "Enter date/time of event"),
            LargeTextEntry(self.event_html_ids["Headline"], "Headline"),
        ]
        return html

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        self.answer_core_plugin_update_reports(htmlResponse, e)
        return [Label("[CORE] Success!")]

    def on_event_request_update(self, e: Event):
        # include hidden assassins if they are already in the event,
        # so that the umpire doesn't accidentally remove them from the event
        assassins = ASSASSINS_DATABASE.get_ident_pseudonym_pairs(include_hidden=lambda a: a.identifier in e.assassins)
        html = [
            HiddenTextbox(self.HTML_SECRET_ID, e.identifier),
            Dependency(
                dependentOn=self.event_html_ids["Assassin Pseudonym"],
                htmlComponents=[
                    AssassinPseudonymPair(self.event_html_ids["Assassin Pseudonym"], "Assassin Pseudonym Selection", assassins, e.assassins),
                    *self.ask_core_plugin_update_reports(e.identifier, standalone=False),
                    Dependency(
                        dependentOn=self.event_html_ids["Kills"],
                        htmlComponents=[
                            AssassinDependentKillEntry(self.event_html_ids["Assassin Pseudonym"], self.event_html_ids["Kills"], "Kills", e.kills)
                        ]
                    )
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
        self.answer_core_plugin_update_reports(htmlResponse, event)
        event.kills = htmlResponse[self.event_html_ids["Kills"]]
        return [Label("[CORE] Success!")]

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

    def on_request_setup_game(self, game_type: str) -> List[HTMLComponent]:
        return [
            *self.ask_set_game_start(),
        ]

    def on_setup_game(self, htmlResponse) -> List[HTMLComponent]:
        return [
            *self.answer_set_game_start(htmlResponse),
        ]

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

    def ask_core_plugin_update_pseudonyms(self, arg: str):
        assassin = ASSASSINS_DATABASE.get(arg)
        return [
            HiddenTextbox(self.HTML_SECRET_ID, assassin.identifier),
            EditablePseudonymList(
                self.html_ids["Pseudonym"], "Edit Pseudonyms",
                (PseudonymData(p, assassin.get_pseudonym_validity(i)) for i, p in enumerate(assassin.pseudonyms))
            ),
        ]

    def answer_core_plugin_update_pseudonyms(self, html_response: Dict):
        ident = html_response[self.HTML_SECRET_ID]
        assassin = ASSASSINS_DATABASE.get(ident)
        # process updates to the assassin's pseudonyms
        pseudonym_updates = html_response[self.html_ids["Pseudonym"]]
        [assassin.add_pseudonym(u.text, u.valid_from) for u in pseudonym_updates.new_values]
        [assassin.edit_pseudonym(i, v.text, v.valid_from) for i, v in pseudonym_updates.edited.items()]
        [assassin.delete_pseudonym(i) for i in pseudonym_updates.deleted_indices]
        return [
            Label(f"[CORE] Successfully updated {ident}'s pseudonyms.")
        ]

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
        event.pluginState["sanity_checks"] = []
        components = []
        for p in PLUGINS:
            components += p.on_event_update(event, html_response_args)
        return components

    def ask_core_plugin_update_reports(self, event_id: str = "", standalone: bool = True) -> List[HTMLComponent]:
        event = EVENTS_DATABASE.get(event_id)

        if standalone:
            # case where this is being used as a standalone export
            assert event is not None
            return [
                HiddenTextbox(self.HTML_SECRET_ID, event_id),
                Dependency(
                    dependentOn=self.event_html_ids["Assassin Pseudonym"],
                    htmlComponents=[
                        HiddenJSON(self.event_html_ids["Assassin Pseudonym"], event.assassins),
                        AssassinDependentReportEntry(self.event_html_ids["Assassin Pseudonym"],
                                                     self.event_html_ids["Reports"], "Reports", event.reports),
                    ]
                ),
            ]
        else:
            # case where using this as part of Event -> Update / Event -> Create
            return [
                AssassinDependentReportEntry(self.event_html_ids["Assassin Pseudonym"], self.event_html_ids["Reports"],
                                             "Reports", event.reports if event else []),
            ]

    def answer_core_plugin_update_reports(self, html_response: Dict, event: Optional[Event] = None) -> List[HTMLComponent]:
        if not event:
            ident = html_response[self.HTML_SECRET_ID]
            event = EVENTS_DATABASE.get(ident)
        event.reports = html_response[self.event_html_ids["Reports"]]
        return [
            Label("[CORE] Successfully updated reports.")
        ]

    def gather_events(self) -> List[Tuple[str, str]]:
        # headline is truncated because `inquirer` doesn't deal with overlong options well
        return [
                (f"[{event.datetime.strftime('%Y-%m-%d %H:%M %p')}] {event.headline[0:25].rstrip()}", identifier)
                for identifier, event in sorted(EVENTS_DATABASE.events.items(), key=lambda x: x[1].datetime, reverse=True)
        ]

    def ask_core_plugin_delete_event(self, event_id: str):
        event = EVENTS_DATABASE.get(event_id)
        return [
            HiddenTextbox(self.HTML_SECRET_ID, event_id),
            Label(f"You are about to delete the event [{event.datetime.strftime('%Y-%m-%d %H:%M %p')}] {event.headline}"),
            *DigitsChallenge(
                identifier_prefix=self.identifier,
                title="Type {digits} to confirm event deletion"
            ),
        ]

    def answer_core_plugin_delete_event(self, html_response_args: Dict):
        ident = html_response_args[self.HTML_SECRET_ID]
        if verify_DigitsChallenge(self.identifier, html_response_args):
            del EVENTS_DATABASE.events[ident]
            return [Label("[CORE] Delete acknowledged.")]
        else:
            return [Label("[CORE] ERROR: Aborting. You entered the code incorrectly.")]

    def ask_core_plugin_update_config(self):
        plugins = [p for p in AVAILABLE_PLUGINS]
        plugins.remove("CorePlugin")
        return [
            SelectorList(
                self.config_html_ids["Plugins"],
                title="Enable or disable plugins",
                options=sorted(plugins),
                defaults=[p for p in plugins if PLUGINS[p].enabled]
            )
        ]

    def answer_core_plugin_update_config(self, htmlResponse):
        enabled_plugins = htmlResponse[self.config_html_ids["Plugins"]]
        enabled_plugins.append("CorePlugin")
        newly_enabled = []
        newly_disabled = []
        for ident, p in AVAILABLE_PLUGINS.items():
            to_enable = (ident in enabled_plugins)
            if to_enable and not p.enabled:
                newly_enabled.append(ident)
            if not to_enable and p.enabled:
                newly_disabled.append(ident)
            p.enabled = to_enable
        return [
            Label(f"[CORE] Successfully {text}abled these plugins: {', '.join(l)}")
            for l, text in ((newly_enabled, "en"), (newly_disabled, "dis")) if l
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

    def ask_reset_database(self) -> List[HTMLComponent]:
        return [
            Label(
                title="Are you sure you want to COMPLETELY RESET the database?"
            ),
            Label(
                title="!!!! UNSAVED DATA CANNOT BE RECOVERED !!!!"
            ),
            Label(
                title="(You can type anything else and the reset will be aborted.)"
            ),
            *DigitsChallenge(
                identifier_prefix=self.identifier,
                title="Type {digits} to reset the database"
            ),
        ]

    def answer_reset_database(self, htmlResponse) -> List[HTMLComponent]:
        if not verify_DigitsChallenge(self.identifier, htmlResponse):
            return [Label("[CORE] Aborting. You entered the code incorrectly.")]
        for f in os.listdir(BASE_WRITE_LOCATION):
            if f.endswith(".json"):
                os.remove(os.path.join(BASE_WRITE_LOCATION, f))
        refresh_databases()
        return [Label("[CORE] Databases successfully reset.")]

    def ask_set_game_start(self):
        return [
            Label("Game start is used for paginating events into week 1, week 2, etc., "
                  "and (if applicable) for calculating incompetence deadlines."),
            DatetimeEntry(
                self.identifier + "_game_start",
                title="Enter game start",
                default=get_game_start()
            ),
        ]

    def answer_set_game_start(self, htmlResponse) -> List[HTMLComponent]:
        set_game_start(htmlResponse[self.identifier + "_game_start"])
        return [
            Label(f"[CORE] Set game start to {get_game_start().strftime('%Y-%m-%d %H:%M:%S')}")
        ]

    def ask_set_game_end(self) -> List[HTMLComponent]:
        default = get_game_end()
        return [
            OptionalDatetimeEntry(
                self.identifier + "_game_end",
                title="Enter game end",
                default=get_now_dt() if default is None else default
            )
        ]

    def answer_set_game_end(self, htmlResponse) -> List[HTMLComponent]:
        new_end = htmlResponse[self.identifier + "_game_end"]
        set_game_end(new_end)
        return [
            Label(f"[CORE] Set game end to {new_end.strftime('%Y-%m-%d %H:%M:%S')}") if new_end
            else Label(f"[CORE] Unset game end.")
        ]

    def gather_game_types(self) -> List[str]:
        return list(GAME_TYPE_PLUGIN_MAP)

    def ask_setup_game(self, game_type: str) -> List[HTMLComponent]:
        # check for missing plugins, and throw error if any required plugins are missing
        missing = [
            plugin for plugin, to_enable in GAME_TYPE_PLUGIN_MAP[game_type].items()
            if to_enable and plugin not in AVAILABLE_PLUGINS
        ]
        if len(missing) > 0:
            return [
                HiddenTextbox(
                    self.config_html_ids["Setup Error"],
                    f"[CORE] Error: Missing required plugin{'s' if len(missing) > 1 else ''} {', '.join(missing)}"
                )
            ]

        components = []
        # enable/disable plugins as specified in GAME_TYPE_PLUGIN_MAP for the selected game type
        for plugin, to_enable in GAME_TYPE_PLUGIN_MAP[game_type].items():
            # still need to check existence of plugin in case a plugin that needs to be *disabled* is missing
            if plugin in AVAILABLE_PLUGINS:
                PLUGINS[plugin].enabled = to_enable
                components.append(Label(f"[CORE] {'En' if to_enable else 'Dis'}abled {plugin}"))

        # require players to be added first.
        # this is done *after* enabling plugins, so that Setup Game can at least help to set up the correct plugins
        if not ASSASSINS_DATABASE.assassins:
            components.append(
                HiddenTextbox(
                    self.config_html_ids["Setup Error"],
                    "[CORE] Error: must add players first."
                )
            )
            return components

        # request components for setup from plugins
        for plugin in PLUGINS:
            components += plugin.on_request_setup_game(game_type)

        return components

    def answer_setup_game(self, htmlResponse) -> List[HTMLComponent]:
        # check for errors
        error = htmlResponse.get(self.config_html_ids["Setup Error"], None)
        if error is not None:
            return [Label(error)]
        # effect config changes
        components = []
        for plugin in PLUGINS:
            components += plugin.on_setup_game(htmlResponse)
        return components
