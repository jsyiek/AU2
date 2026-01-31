import csv
import urllib.request
import os
import re
from typing import List, Optional

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.model import Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.NamedSmallTextbox import NamedSmallTextbox
from AU2.html_components.SimpleComponents.PathEntry import PathEntry
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WATER_STATUSES

GSHEET_SHARE_LINK_PATTERN = re.compile(r"docs.google.com/spreadsheets/d/([^/]+)/")

@registered_plugin
class PlayerImporterPlugin(AbstractPlugin):

    def __init__(self):
        super().__init__("PlayerImporterPlugin")
        self.html_ids = {
            "CSV Path": self.identifier + "_csv",
            "GSheets URL": self.identifier + "_gsheet_url"
        }

        self.expected_columns = ["real_name", "pseudonym", "pronouns", "email", "college", "address", "water_status", "notes", "is_police"]

        self.exports = [
            Export(
                identifier="player_importer_import_players",
                display_name="Import players from CSV file",
                ask=self.ask_read_assassins_csv,
                answer=self.answer_read_assassins_csv,
            ),
            Export(
                identifier="player_importer_google_sheets",
                display_name="Import players from Google Sheets",
                ask=self.ask_read_assassins_gsheets,
                answer=self.answer_read_assassins_gsheets,
            )
        ]

    def required_fields_explanation(self) -> List[HTMLComponent]:
        return [
            Label(
                title="Required fields:"
            ),
            Label(
                title=", ".join(self.expected_columns)
            ),
            Label(title="('is_police' will check if the answer is 'yes' and set police accordingly)"),
            Label(
                title="NOTE: If you don't do this, the player importer will make a best effort attempt to "
                      "guess what your fields mean"
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
        ] + self.required_fields_explanation() + [
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
                    or field == "is_police" and any(x in inp for x in ('police', 'watch', 'casual')):
                return field

    def guess_if_police(self, field) -> bool:
        possible_police = [
            "police",
            "yes",
            "casual",
            "watch",
        ]
        return any(f in field.lower() for f in possible_police)

    def guess_water_status(self, field) -> str:
        field = field.lower()
        if "care" in field:
            return WATER_STATUSES[1]
        elif "full" in field:
            return WATER_STATUSES[2]
        return WATER_STATUSES[0]

    def read_assassins(self, rows: List[List[str]]) -> List[HTMLComponent]:
        index_mapping = {}

        # ignore any empty rows above the header
        header_row = 0
        while len(index_mapping) == 0 and header_row < len(rows):
            headers = rows[header_row]
            for h in headers:
                field = self.guess_field(h)
                if field is not None:
                    index_mapping[field] = headers.index(h)
            header_row += 1

        if len(index_mapping) != len(self.expected_columns):
            failures = ', '.join([e for e in self.expected_columns if e not in index_mapping])
            return [Label(title=f"[IMPORTER] ERROR: Failed to identify these fields: {failures}")]

        assassins = []
        for r in rows[header_row:]:
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

    def answer_read_assassins_csv(self, htmlResponse) -> List[HTMLComponent]:
        csv_path = htmlResponse[self.html_ids["CSV Path"]]
        csv_path = os.path.expanduser(csv_path)
        if not os.path.exists(csv_path):
            return [Label(title=f"[IMPORTER] ERROR: File not found: {csv_path}")]
        if os.path.isdir(csv_path):  # shouldn't be necessary, but you never know...
            return [Label(title=f"[IMPORTER] ERROR: Path is a directory: {csv_path}")]

        rows: list
        try:
            with open(csv_path, "r") as F:
                rows = [r for r in csv.reader(F)]
        except PermissionError:
            return [Label(title=f"[IMPORTER] ERROR: Lacking permission for: {csv_path}")]

        return self.read_assassins(rows)

    def ask_read_assassins_gsheets(self) -> List[HTMLComponent]:
        return [
            Label(
                title="This player importer requires a specific spreadsheet format."
            ),
        ] + self.required_fields_explanation() + [
            Label(
                title="The spreadsheet must be publicly accessible for AU2 to import from it."
            ),
            Label(
                title="After AU2 has imported players you can set the sheet to private again."
            ),
            NamedSmallTextbox(
                title="Answer anything to this textbox to confirm you've read what is said above.",
                identifier="doesntmatter"
            ),
            NamedSmallTextbox(
                identifier=self.html_ids["GSheets URL"],
                title="URL of Google sheet to import players from"
            )
        ]

    def answer_read_assassins_gsheets(self, htmlResponse) -> List[HTMLComponent]:
        gsheet_url = htmlResponse[self.html_ids["GSheets URL"]]
        matches = GSHEET_SHARE_LINK_PATTERN.findall(gsheet_url)
        if len(matches) == 0:
            return [Label(title=f"[IMPORTER] ERROR: Invalid Google Sheet URL.")]
        gsheet_id = matches[0]
        try:
            response = urllib.request.urlopen(f"https://docs.google.com/spreadsheets/export?exportFormat=csv&id={gsheet_id}")
        except Exception as e:
            return [Label(title=f"[IMPORTER] ERROR: Could not access sheet. Found error: {e}")]
        lines = [l.decode('utf-8') for l in response.readlines()]
        rows = [r for r in csv.reader(lines)]
        return self.read_assassins(rows)
