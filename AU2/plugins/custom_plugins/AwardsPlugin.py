import re

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from dataclasses_json import dataclass_json

from AU2 import ROOT_DIR, BASE_WRITE_LOCATION
from AU2.database.model.PersistentFile import PersistentFile
from AU2.database import ALL_DATABASES
from AU2.html_components.HTMLComponent import HTMLComponent
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.HtmlEntry import HtmlEntry
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.Table import Table
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export, NavbarEntry
from AU2.plugins.constants import DEFAULT_AWARDS, WEBPAGE_WRITE_LOCATION
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.util.date_utils import get_now_dt, get_term
from AU2.plugins.util.game import get_game_start

AWARD_TEMPLATE = """
<dt id = '{KEY}'><span class='{KEY}'>{AWARD_NAME}:</span></dt>
<dd>
<strong>{AWARD_RECIPIENT}</strong>, {AWARD_REASON}<br />
{HONOURABLE_MENTIONS}</dd>

"""

AWARD_DATA_TEMPLATE = "{AWARD_NAME}: {WINNER}"

AWARDS_NAVBAR_ENTRY = NavbarEntry("awards.html", "Awards", -3)

AWARDS_PAGE_TEMPLATE: str
with open(ROOT_DIR / "plugins" / "custom_plugins" / "html_templates" / "awards.html", "r", encoding="utf-8",
          errors="ignore") as F:
    AWARDS_PAGE_TEMPLATE= F.read()

# regex patterns from archive_collated_awards.php
AWARD_NAME_PATTERN = re.compile(r"^ *The (.*) for (.*) *$", flags=re.IGNORECASE)
KEY_TRANSFORMATION_PATTERN = re.compile(r"[^A-Za-z]+")

# pattern to ignore an initial 'The'
INITIAL_THE_PATTERN = re.compile(r"^\s*The ", flags=re.IGNORECASE)


def parse_award_name(full_name: str) -> (str, str):
    """Parses a full award name into the format used internally by AwardsPlugin

    Args:
        full_name (str): Full award name. Must be of form "The X for Y".

    Returns:
        str, str: the tuple (X, Y)

    Examples:
        >>> parse_award_name("The 'Ginger Cake' Award for the 'Smoothest' Kill")
        ("'Ginger Cake' Award", "the 'Smoothest' Kill")
    """
    m = AWARD_NAME_PATTERN.match(full_name)
    return m[1], m[2]


def render_award_name(name: (str, str)) -> str:
    """A (right) inverse of `parse_award_name`"""
    return f"The {name[0]} for {name[1]}"


def award_type_to_key(award_type: str) -> str:
    """Converts an award reason (part of the award name after 'for') into the corresponding key used as its CSS class,
    and by archive_collated_awards.php to count two awards as 'the same' and to link from that page to the original
    award.

    Args:
        award_type (str): The part of an award name after 'for', defining the award.

    Returns:
        str: the award's "key"

    Examples:
        >>> award_type_to_key("the 'Smoothest' Kill")
        "thesmoothestkill"
    """
    return KEY_TRANSFORMATION_PATTERN.sub("", award_type).lower()


# parse default awards to more convenient format
DEFAULT_AWARDS_MAP = {award_type_to_key(n[1]): n for n in (parse_award_name(full_name) for full_name in DEFAULT_AWARDS)}


@dataclass_json
@dataclass
class Award(PersistentFile):
    """
    Class for storing an award in the database.
    """
    name: (str, str)
    recipient_name: str
    recipient_reason: str
    honourable_mentions: str

    def get_key(self) -> str:
        """The 'key' used to identify awards for the purposes of collation"""
        return award_type_to_key(self.name[1])

@dataclass_json
@dataclass
class AwardsDatabase(PersistentFile):
    WRITE_LOCATION = BASE_WRITE_LOCATION / "AwardsDatabase.json"
    awards: Dict[str, Award]  = field(default_factory=dict) # map {key: award}

    def add(self, award: Award):
        self.awards[award.get_key()] = award

    def delete(self, award_key: str):
        """Removes an award from the database, if it exists"""
        if award_key in self.awards:
            del self.awards[award_key]

    def _refresh(self):
        """
        Forces a refresh of the underlying database
        """
        if self.TEST_MODE:
            self.awards = {}
            return

        self.awards = self.load().awards


@registered_plugin
class AwardsPlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("AwardsPlugin")

        self.html_ids = {
            "Award Key": self.identifier + "_key",
            "Award Type": self.identifier + "_award_type",
            "Award Name": self.identifier + "_award_name",
            "Award Recipient": self.identifier + "_award_recipient",
            "Award Reason": self.identifier + "_award_reason",
            "Honourable Mentions": self.identifier + "_honourable_mentions",
            "Confirm Delete": self.identifier + "_confirm_delete",
        }

        self.exports = [
            Export(
                "awards_add",
                "Awards -> Create",
                self.ask_award_create_or_update,
                self.answer_award_create_or_update,
                options_functions=(self.gather_unclaimed_awards,)
            ),
            Export(
                "awards_update",
                "Awards -> Update",
                self.ask_award_create_or_update,
                self.answer_award_create_or_update,
                options_functions=(self.gather_awards,),
            ),
            Export(
                "awards_delete",
                "Awards -> Delete",
                self.ask_award_delete,
                self.answer_award_delete,
                options_functions=(self.gather_awards,),
            ),
        ]

        self.AWARDS_DATABASE = AwardsDatabase.load()
        ALL_DATABASES.append(self.AWARDS_DATABASE)

    def gather_unclaimed_awards(self) -> List[Tuple[str, str]]:
        """Returns a list of the default awards that have not yet been assigned to someone, plus a *CUSTOM* option for new awards"""
        return [
            (name[1], key) for key, name in DEFAULT_AWARDS_MAP.items() if key not in self.AWARDS_DATABASE.awards
        ] + [("*CUSTOM*", "")]

    def ask_award_create_or_update(self, award_key: str) -> List[HTMLComponent]:
        award = self.AWARDS_DATABASE.awards.get(award_key)
        is_custom = award_key not in DEFAULT_AWARDS_MAP
        return [
            (
                DefaultNamedSmallTextbox(
                    identifier=self.html_ids["Award Type"],
                    title="What the award is for (generically)",
                    default=award.name[1] if award else "",
                ) if is_custom else HiddenTextbox(self.html_ids["Award Type"], DEFAULT_AWARDS_MAP[award_key][1])
            ),
            HiddenTextbox(self.html_ids["Award Key"], award_key),
            DefaultNamedSmallTextbox(
                identifier=self.html_ids["Award Name"],
                title="Part of award name BEFORE 'for'",
                default=award.name[0] if award else DEFAULT_AWARDS_MAP.get(award_key, ("",))[0]
            ),
            DefaultNamedSmallTextbox(
                identifier=self.html_ids["Award Recipient"],
                title="Name(s) of award recipient(s)",
                default=award.recipient_name if award else ""
            ),
            HtmlEntry(
                identifier=self.html_ids["Award Reason"],
                title="Reason for the award",
                short=True,
                default=award.recipient_reason if award else "for ",
            ),
            HtmlEntry(
                identifier=self.html_ids["Honourable Mentions"],
                title="Honourable mentions",
                default=award.honourable_mentions if award else "",
            )
        ]

    def answer_award_create_or_update(self, html_response) -> List[HTMLComponent]:
        award_key = html_response[self.html_ids["Award Key"]]
        self.AWARDS_DATABASE.delete(award_key)
        award_firstname = INITIAL_THE_PATTERN.sub("", html_response[self.html_ids["Award Name"]])
        award = Award(
            name = (award_firstname, html_response[self.html_ids["Award Type"]]),
            recipient_name = html_response[self.html_ids["Award Recipient"]],
            recipient_reason = html_response[self.html_ids["Award Reason"]],
            honourable_mentions = html_response[self.html_ids["Honourable Mentions"]],
        )
        self.AWARDS_DATABASE.add(award)
        return [Label(f"[AWARDS] Awarded {render_award_name(award.name)} to {award.recipient_name}")]

    def gather_awards(self) -> List[Tuple[str, str]]:
        """Lists awards already in the database"""
        return [(f"{render_award_name(award.name)}: {award.recipient_name}", key) for key, award in self.AWARDS_DATABASE.awards.items()]

    def ask_award_delete(self, award_key: str) -> List[HTMLComponent]:
        award = self.AWARDS_DATABASE.awards[award_key]
        return [
            Table([
                ("Name", render_award_name(award.name)),
                ("Recipient", f"{award.recipient_name}, {award.recipient_reason}"),
                ("Honourable mentions", award.honourable_mentions),
            ]),
            # We don't need to be particularly careful about deleting awards,
            # hence use a Checkbox rather than a DigitsChallenge
            Checkbox(
                self.html_ids["Confirm Delete"],
                "Delete the above award?"
            ),
            HiddenTextbox(self.html_ids["Award Key"], award_key),
        ]

    def answer_award_delete(self, html_response) -> List[HTMLComponent]:
        if html_response[self.html_ids["Confirm Delete"]]:
            self.AWARDS_DATABASE.delete(html_response[self.html_ids["Award Key"]])
            return [Label("[AWARDS] Deleted award.")]
        else:
            return [Label("[AWARDS] Did not delete award.")]

    def on_page_generate(self, html_response: dict, navbar_entries: List[NavbarEntry]) -> List[HTMLComponent]:
        components = []
        if self.AWARDS_DATABASE.awards:
            award_data = "\n".join(
                AWARD_DATA_TEMPLATE.format(AWARD_NAME=render_award_name(award.name), WINNER=award.recipient_name)
                for award in self.AWARDS_DATABASE.awards.values()
            )
            award_html = "\n".join(
                AWARD_TEMPLATE.format(
                    KEY=award.get_key(),
                    AWARD_NAME=render_award_name(award.name),
                    AWARD_RECIPIENT=award.recipient_name,
                    AWARD_REASON=award.recipient_reason,
                    HONOURABLE_MENTIONS=award.honourable_mentions,
                )
                for award in self.AWARDS_DATABASE.awards.values()
            )
            with open(WEBPAGE_WRITE_LOCATION / AWARDS_NAVBAR_ENTRY.url, "w+", encoding="utf-8") as F:
                F.write(
                    AWARDS_PAGE_TEMPLATE.format(
                        YEAR=get_now_dt().year,
                        AWARD_HTML=award_html,
                        AWARD_DATA=award_data,
                        TERM=get_term(get_game_start())
                    )
                )
            navbar_entries.append(AWARDS_NAVBAR_ENTRY)
            components.append(Label("[AWARDS] Success!"))
        return components
