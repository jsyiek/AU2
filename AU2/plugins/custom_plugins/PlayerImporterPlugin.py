import csv
import os
from typing import List, Optional

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.model import Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.Label import Label
from AU2.html_components.NamedSmallTextbox import NamedSmallTextbox
from AU2.html_components.PathEntry import PathEntry
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WATER_STATUSES


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
            Label(
                title="NOTE: If you don't do this, the player importer will make a best effort attempt to "
                      "guess what your fields mean"
            ),
            NamedSmallTextbox(
                title="Answer anything to this textbox to confirm you've read what is said above.",
                identifier="doesntmatter"
            ),
            PathEntry(
                identifier=self.html_ids["CSV Path"],
                title="Path to CSV to import"
            )
        ]

    def guess_field(self, inp) -> Optional[str]:
        inp = inp.lower()
        for field in self.expected_columns:
            if field == inp:
                return field
        for field in self.expected_columns:
            # notes to the umpires can be mixed up for regular game notes
            if "umpire" in inp and "note" in inp:
                continue
            if any(f in inp for f in [field, field.replace("_", " ")]):
                return field
            elif field == "real_name" and "name" in inp \
                    or field == "is_police" and "police" in inp:
                return field

    def guess_if_police(self, field) -> bool:
        possible_police = [
            "police",
            "yes",
            "casual"
        ]
        return any(f in field.lower() for f in possible_police)

    def guess_water_status(self, field) -> str:
        field = field.lower()
        if "care" in field:
            return WATER_STATUSES[1]
        elif "full" in field:
            return WATER_STATUSES[2]
        return WATER_STATUSES[0]

    def answer_read_assassins_csv(self, htmlResponse) -> List[HTMLComponent]:
        csv_path = htmlResponse[self.html_ids["CSV Path"]]
        csv_path = os.path.expanduser(csv_path)
        if not os.path.exists(csv_path):
            return [Label(title=f"[IMPORTER] ERROR: File not found: {csv_path}")]

        rows: list
        with open(csv_path, "r") as F:
            rows = [r for r in csv.reader(F)]

        headers = rows[0]
        index_mapping = {}
        for h in headers:
            field = self.guess_field(h)
            if field is not None:
                index_mapping[field] = headers.index(h)

        if len(index_mapping) != len(self.expected_columns):
            failures = ', '.join([e for e in self.expected_columns if e not in index_mapping])
            return [Label(title=f"[IMPORTER] ERROR: Failed to identify these fields: {failures}")]

        assassins = []
        for r in rows[1:]:
            params = {}
            try:
                for (e, i) in index_mapping.items():
                    arg = r[i]
                    if e == "pseudonym":
                        params["pseudonyms"] = [arg.strip()]
                    elif e == "is_police":
                        params["is_police"] = self.guess_if_police(arg)
                    elif e == "water_status":
                        params["water_status"] = self.guess_water_status(arg)
                    else:
                        params[e] = arg.strip()
                a = Assassin(**params)
                assassins.append(a)
            except Exception as e:
                return [Label(title=f"[IMPORTER] ERROR: Could not create assassin. Found error: {e}")]

        for a in assassins:
            ASSASSINS_DATABASE.add(a)

        return [Label(title="[IMPORTER] Success!")]

