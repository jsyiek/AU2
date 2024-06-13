from datetime import datetime
from typing import Dict, List

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
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
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.AvailablePlugins import __PluginMap
from AU2.plugins.constants import COLLEGES, WATER_STATUSES
from AU2.plugins.custom_plugins.BackupPlugin import BackupPlugin
from AU2.plugins.custom_plugins.MafiaPlugin import MafiaPlugin
from AU2.plugins.custom_plugins.PlayerImporterPlugin import PlayerImporterPlugin
from AU2.plugins.custom_plugins.WantedPlugin import WantedPlugin

# Add plugins here
# Note that importing this dictionary and adding to it will NOT necessarily
# make it a functional plugin! Don't do this!
AVAILABLE_PLUGINS = {}


class CorePlugin(AbstractPlugin):
    HTML_SECRET_ID: str = "CorePlugin_identifier"

    def __init__(self):
        super().__init__("CorePlugin")

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
                (lambda: [v for v in ASSASSINS_DATABASE.assassins],)
            ),
            Export(
                "core_event_create_event",
                "Event -> Create",
                self.ask_core_plugin_create_event,
                self.answer_core_plugin_create_event
            ),
            Export(
                "core_event_update_event",
                "Event -> Update",
                self.ask_core_plugin_update_event,
                self.answer_core_plugin_update_event,
                (lambda: [v for v in EVENTS_DATABASE.events],)
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
            NamedSmallTextbox(self.html_ids["Notes"], "Notes"),
            Checkbox(self.html_ids["Police"], "Police? (y/n)")
        ]
        return html

    def on_assassin_create(self, assassin: Assassin, htmlResponse) -> List[HTMLComponent]:
        return [Label("[CORE] Success!")]

    def on_assassin_request_update(self, assassin):
        html = [
            HiddenTextbox(CorePlugin.HTML_SECRET_ID, assassin.identifier),
            ArbitraryList(self.html_ids["Pseudonym"], "Pseudonyms", assassin.pseudonyms),
            DefaultNamedSmallTextbox(self.html_ids["Real Name"], "Real Name", assassin.real_name),
            DefaultNamedSmallTextbox(self.html_ids["Pronouns"], "Pronouns", assassin.pronouns),
            DefaultNamedSmallTextbox(self.html_ids["Email"], "Email", assassin.email, type_="email"),
            DefaultNamedSmallTextbox(self.html_ids["Address"], "Address", assassin.address),
            InputWithDropDown(self.html_ids["Water Status"], "Water Status", WATER_STATUSES, selected=assassin.water_status),
            InputWithDropDown(self.html_ids["College"], "College", COLLEGES, selected=assassin.college),
            DefaultNamedSmallTextbox(self.html_ids["Notes"], "Notes", assassin.notes),
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
            DatetimeEntry(self.event_html_ids["Datetime"], "Date/time of event"),
            LargeTextEntry(self.event_html_ids["Headline"], "Headline"),
        ]
        return html

    def on_event_create(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return [Label("[CORE] Success!")]

    def on_event_request_update(self, e: Event):
        assassins = [(a.identifier, a.pseudonyms) for a in ASSASSINS_DATABASE.assassins.values()]
        html = [
            HiddenTextbox(CorePlugin.HTML_SECRET_ID, e.identifier),
            Dependency(
                dependentOn=self.event_html_ids["Assassin Pseudonym"],
                htmlComponents=[
                    AssassinPseudonymPair(self.event_html_ids["Assassin Pseudonym"], "Assassin Pseudonym Selection", assassins, e.assassins),
                    AssassinDependentReportEntry(self.event_html_ids["Assassin Pseudonym"], self.event_html_ids["Reports"], "Reports", e.reports),
                    AssassinDependentKillEntry(self.event_html_ids["Assassin Pseudonym"], self.event_html_ids["Kills"], "Kills", e.kills)
                ]
            ),
            DatetimeEntry(self.event_html_ids["Datetime"], "Date/time of event", e.datetime),
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
        ident = html_response_args[CorePlugin.HTML_SECRET_ID]
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
        ident = html_response_args[CorePlugin.HTML_SECRET_ID]
        event = EVENTS_DATABASE.get(ident)
        components = []
        for p in PLUGINS:
            components += p.on_event_update(event, html_response_args)
        return components


# Add new plugins to this dictionary
# TODO: This is a hack. Make it a config file (or better yet, write a plugin to manage this).
AVAILABLE_PLUGINS["CorePlugin"] = CorePlugin()
AVAILABLE_PLUGINS["WantedPlugin"] = WantedPlugin()
AVAILABLE_PLUGINS["MafiaPlugin"] = MafiaPlugin()
AVAILABLE_PLUGINS["BackupPlugin"] = BackupPlugin()
AVAILABLE_PLUGINS["PlayerImporterPlugin"] = PlayerImporterPlugin()
PLUGINS = __PluginMap(AVAILABLE_PLUGINS)


if __name__ == "__main__":
    print(PLUGINS["CorePlugin"].exports[0].ask())

    html_response_args = {
        PLUGINS["CorePlugin"].html_ids["Pseudonym"]: "Vendetta",
        PLUGINS["CorePlugin"].html_ids["Real Name"]: "Ben",
        PLUGINS["CorePlugin"].html_ids["Email"]: "e@ma.il",
        PLUGINS["CorePlugin"].html_ids["Address"]: "Whitehouse",
        PLUGINS["CorePlugin"].html_ids["Water Status"]: "No Water",
        PLUGINS["CorePlugin"].html_ids["College"]: "Yes",
        PLUGINS["CorePlugin"].html_ids["Notes"]: "Some",
        PLUGINS["CorePlugin"].html_ids["Police"]: False
    }

    print(PLUGINS["CorePlugin"].exports[0].answer(html_response_args))
    print(ASSASSINS_DATABASE)
    exp1 = PLUGINS["CorePlugin"].exports[1]
    args = [f() for f in exp1.options_functions]
    print(args)
    print(exp1.ask(args[0][0]))

    html_response_args = {
        PLUGINS["CorePlugin"].HTML_SECRET_ID: "Ben (Vendetta) ID: 0",
        PLUGINS["CorePlugin"].html_ids["Pseudonym"]: ["Vendetta"],
        PLUGINS["CorePlugin"].html_ids["Real Name"]: "Ben Syiek",
        PLUGINS["CorePlugin"].html_ids["Email"]: "e@ma.il",
        PLUGINS["CorePlugin"].html_ids["Address"]: "10 Downing Street",
        PLUGINS["CorePlugin"].html_ids["Water Status"]: "No Water",
        PLUGINS["CorePlugin"].html_ids["College"]: "Homerton College",
        PLUGINS["CorePlugin"].html_ids["Notes"]: "Some",
        PLUGINS["CorePlugin"].html_ids["Police"]: False
    }
    print(exp1.answer(html_response_args))
    print(ASSASSINS_DATABASE)

    print(PLUGINS["CorePlugin"].exports[2].ask())

    core = PLUGINS["CorePlugin"]
    html_response_args = {
        core.event_html_ids["Assassin Pseudonym"]: {"jamie": 0, "thomas": 0},
        core.event_html_ids["Datetime"]: datetime(year=2024, month=6, day=11, hour=17, minute=30),
        core.event_html_ids["Headline"]: "[P1] has submitted an event!",
        core.event_html_ids["Reports"]: {("jamie", 0): "a report"},
        core.event_html_ids["Kills"]: [("jamie", "thomas")]
    }
    print(core.event_html_ids["Assassin Pseudonym"])
    print(PLUGINS["CorePlugin"].exports[2].answer(html_response_args))
    print(EVENTS_DATABASE)

    html_response_args = {
        core.HTML_SECRET_ID: "(1) [P1] has submitted an event!",
        core.event_html_ids["Assassin Pseudonym"]: {"doug": 0, "thomas": 0},
        core.event_html_ids["Datetime"]: datetime(year=2023, month=6, day=11, hour=17, minute=30),
        core.event_html_ids["Headline"]: "[P1] has submitted an event! AGAIN!",
        core.event_html_ids["Reports"]: {("doug", 0): "a report"},
        core.event_html_ids["Kills"]: [("doug", "thomas")]
    }
    print(core.exports[3].ask("(1) [P1] has submitted an event!"))
    print(core.exports[3].answer(html_response_args))
    print(EVENTS_DATABASE)
    EVENTS_DATABASE.save()
