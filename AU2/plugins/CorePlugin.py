from typing import Dict

from AU2 import CoreModelManager
from AU2.database.model import Assassin
from AU2.html_components.InputWithDropDown import InputWithDropDown
from AU2.html_components.NamedSmallTextbox import NamedSmallTextbox
from AU2.plugins.AbstractPlugin import AbstractPlugin
from AU2.plugins.ConfigLoader import PLUGINS
from AU2.plugins.constants import COLLEGES, WATER_STATUSES


class Core(AbstractPlugin):

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

    def on_assassin_request_create(self):
        html = [
            NamedSmallTextbox(self.html_ids["Pseudonym"], "Initial Pseudonym"),
            NamedSmallTextbox(self.html_ids["Real Name"], "Real Name"),
            NamedSmallTextbox(self.html_ids["Email"], "Email", type_="email"),
            NamedSmallTextbox(self.html_ids["Address"], "Address"),
            InputWithDropDown(self.html_ids["Water Status"], "Water Status", WATER_STATUSES)
            InputWithDropDown(self.html_ids["College"], "College", COLLEGES),
            NamedSmallTextbox(self.html_ids["Notes"], "Notes"),
            NamedSmallTextbox(self.html_ids["Police"], "Police? (y/n)")
        ]
        return html
    
    def core_plugin_create_assassin(self, html_response_args: Dict[str, str]):
        args = []
        for id_ in self.html_ids_list:
            args.append(html_response_args[id_])
        assassin = Assassin(*args)
        for p in PLUGINS:
            p.on_assassin_create(assassin, html_response_args)
        CoreModelManager.add_assassin(assassin)
