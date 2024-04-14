from typing import Dict

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.model import Assassin
from AU2.html_components.InputWithDropDown import InputWithDropDown
from AU2.html_components.Label import Label
from AU2.html_components.NamedSmallTextbox import NamedSmallTextbox
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.AvailablePlugins import __PluginMap
from AU2.plugins.constants import COLLEGES, WATER_STATUSES

# Add plugins here
# Note that importing this dictionary and adding to it will NOT necessarily
# make it a functional plugin! Don't do this!
AVAILABLE_PLUGINS = { }

class CorePlugin(AbstractPlugin):

    def __init__(self):
        super().__init__("CorePlugin")

        self.html_ids_list = [
            "Pseudonym",
            "Real Name",
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
            "Email": self.identifier + "_email",
            "Address": self.identifier + "_address",
            "Water Status": self.identifier + "_water_status",
            "College": self.identifier + "_college",
            "Notes": self.identifier + "_notes",
            "Police": self.identifier + "_police"
        }

        self.exports = [
            Export(
                "core_assassin_create_assassin",
                "Assassin -> Create",
                self.ask_core_plugin_create_assassin,
                self.answer_core_plugin_create_assassin
            )
        ]

    def on_assassin_request_create(self):
        html = [
            NamedSmallTextbox(self.html_ids["Pseudonym"], "Initial Pseudonym"),
            NamedSmallTextbox(self.html_ids["Real Name"], "Real Name"),
            NamedSmallTextbox(self.html_ids["Email"], "Email", type_="email"),
            NamedSmallTextbox(self.html_ids["Address"], "Address"),
            InputWithDropDown(self.html_ids["Water Status"], "Water Status", WATER_STATUSES),
            InputWithDropDown(self.html_ids["College"], "College", COLLEGES),
            NamedSmallTextbox(self.html_ids["Notes"], "Notes"),
            NamedSmallTextbox(self.html_ids["Police"], "Police? (y/n)")
        ]
        return html

    def ask_core_plugin_create_assassin(self):
        components = []
        for p in PLUGINS:
            components += p.on_assassin_request_create()
        return components

    def answer_core_plugin_create_assassin(self, html_response_args: Dict[str, str]):
        # TODO: This function needs to parse the arguments properly (e.g., Pseudonym should be a list)
        args = []
        for id_ in self.html_ids_list:
            args.append(html_response_args[id_])
        assassin = Assassin(*args)
        return_components = [Label("Input successful!")]
        for p in PLUGINS:
            return_components += p.on_assassin_create(assassin, html_response_args)
        ASSASSINS_DATABASE.add(assassin)
        return return_components


# Add new plugins to this dictionary
AVAILABLE_PLUGINS["CorePlugin"] = CorePlugin()
PLUGINS = __PluginMap(AVAILABLE_PLUGINS)


if __name__ == "__main__":
    print(PLUGINS["CorePlugin"].exports[0].ask())

    html_response_args = {
        "Pseudonym": "Vendetta",
        "Real Name": "Ben",
        "Email": "e@ma.il",
        "Address": "Whitehouse",
        "Water Status": "No Water",
        "College": "Yes",
        "Notes": "Some",
        "Police": False
    }

    print(PLUGINS["CorePlugin"].exports[0].answer(html_response_args))
    print(ASSASSINS_DATABASE)
