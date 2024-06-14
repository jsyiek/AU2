import csv
import os
from typing import List

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.model import Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.Label import Label
from AU2.html_components.NamedSmallTextbox import NamedSmallTextbox
from AU2.html_components.PathEntry import PathEntry
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin


@registered_plugin
class PlayerImporterPlugin(AbstractPlugin):

    def __init__(self):
        super().__init__("PlayerImporterPlugin")
        self.html_ids = {
            "CSV Path": self.identifier + "_csv"
        }

        self.expected_columns = ["real_name", "pseudonym", "pronouns", "email", "college", "address", "water_status", "notes", "is_police"]

        self.exports = [
            Export(
                identifier="import_players",
                display_name="Import players",
                ask=self.ask_read_assassins_csv,
                answer=self.answer_read_assassins_csv,
            )
        ]

    def ask_read_assassins_csv(self) -> List[HTMLComponent]:
        return [
            Label(
                title="This player importer requires a specific CSV format"
            ),
            Label(
                title="Must use comma separation"
            ),
            Label(
                title="Required fields:"
            ),
            Label(
                title="     real_name,pseudonym,pronouns,email,college,address,water_status,notes,is_police"
            ),
            Label(title="('is_police' will check if the answer is 'yes' in lower case and set police accordingly)"),
            NamedSmallTextbox(
                title="Answer anything to this textbox to confirm you've read what is said above.",
                identifier="doesntmatter"
            ),
            PathEntry(
                identifier=self.html_ids["CSV Path"],
                title="Path to CSV to import"
            )
        ]

    def answer_read_assassins_csv(self, htmlResponse) -> List[HTMLComponent]:
        csv_path = htmlResponse[self.html_ids["CSV Path"]]
        csv_path = os.path.expanduser(csv_path)
        if not os.path.exists(csv_path):
            return [Label(title=f"[IMPORTER] ERROR: File not found: {csv_path}")]

        rows = []
        with open(csv_path, "r") as F:
            rows = [r for r in csv.reader(F)]

        headers = rows[0]
        index_mapping = {}
        for e in self.expected_columns:
            if e not in headers:
                return [Label(title=f"[IMPORTER] ERROR: Read CSV file but couldn't find header {e}")]
            index_mapping[e] = headers.index(e)

        assassins = []
        for r in rows[1:]:
            params = {}
            try:
                for (e, i) in index_mapping.items():
                    arg = r[i]
                    if e == "pseudonym":
                        params["pseudonyms"] = [arg]
                    elif e == "is_police":
                        params["is_police"] = arg == "yes"
                    else:
                        params[e] = arg
                a = Assassin(**params)
                assassins.append(a)
            except Exception as e:
                return [Label(title=f"[IMPORTER] ERROR: Could not create assassin. Found error: {e}")]

        for a in assassins:
            ASSASSINS_DATABASE.add(a)

        return [Label(title="[IMPORTER] Success!")]

