import re

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from dataclasses_json import dataclass_json

from AU2 import ROOT_DIR, BASE_WRITE_LOCATION
from AU2.database.model.PersistentFile import PersistentFile
from AU2.html_components.HTMLComponent import HTMLComponent
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.HtmlEntry import HtmlEntry
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.Table import Table
from AU2.html_components.SpecialComponents.AwardNameEntry import AwardNameEntry
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export, NavbarEntry
from AU2.plugins.CorePlugin import registered_plugin

AWARD_TEMPLATE = """
<dt id = '{KEY}'><span class='{KEY}'>{AWARD_NAME}:</span></dt><dd>{AWARD_BODY}</br></dd>

"""

AWARDS_NAVBAR_ENTRY = NavbarEntry("awards.html", "Awards", -2)

AWARDS_PAGE_TEMPLATE: str
with open(ROOT_DIR / "plugins" / "custom_plugins" / "html_templates" / "bounties.html", "r", encoding="utf-8",
          errors="ignore") as F:
    BOUNTIES_PAGE_TEMPLATE = F.read()

AWARD_NAME_PATTERN = re.compile(r"^ *The (.*) for (.*) *$", flags=re.IGNORECASE)  # note: this is the regex from archive_collated_awards.php
HTML_COMMENT_PATTERN = re.compile(r"<!--(?:(?!-->).)*-->", flags=re.MULTILINE | re.DOTALL)
WHITESPACE_PATTERN = re.compile(r"\s")

AWARD_BODY_INSTRUCTIONS = """
<!--
Here you can enter the HTML to be displayed under the award.
Text inside HTML comment blocks, such as these instructions will be deleted by AU2.
The code [R] will be substituted with the award recipient as previously entered.
By convention, you should wrap the names of recipients of 'honourable mentions' in <strong> tags (i.e. "<strong>Recipent name</strong>").
-->
"""

SUGGESTED_AWARDS = [

]


@dataclass_json
@dataclass
class Award(PersistentFile):
    """
    Class for storing an award in the database.

    Attributes:
        name ((str, str)): For compatibility with the collated awards page, all awards must be of the form
            "The [AWARD NAME] for [AWARD REASON]", as two awards are considered the "same" if [AWARD REASON] is the same
            for both. So we store the name as tuple ([AWARD NAME], [AWARD REASON]).
        body (str): The HTML to be displayed under the award name.
        winner (str): Winner of the award for the purposes of collation, and substituting [R] in the Award `body`.
    """
    name: (str, str)
    body: str
    winner: str

    def render_name(self) -> str:
        """The award name as rendered on the page / in the UI"""
        award_name, award_reason = self.name
        return f"The {award_name.title()} for {award_reason.title()}"

    def get_key(self) -> str:
        """The 'key' used to identify awards for the purposes of collation"""
        return WHITESPACE_PATTERN.sub("", self.name[1]).lower()

    @classmethod
    def parse_name(cls, name: str) -> (str, str):
        """Parses names of the form 'The [AWARD NAME] for [AWARD REASON] into a tuple"""
        match = AWARD_NAME_PATTERN.match(name)
        return match[1], match[2]


@dataclass_json
@dataclass
class AwardsDatabase(PersistentFile):
    WRITE_LOCATION = BASE_WRITE_LOCATION / "AwardsDatabase.json"
    awards: List[Award] = field(default_factory=list)

    def add(self, award: Award):
        self.awards.append(award)

    def get(self, key: str) -> Optional[Award]:
        for award in self.awards:
            if award.get_key() == key:
                return award
        return None

    def delete(self, key: str):
        for i, award in enumerate(self.awards):
            if award.get_key() == key:
                self.awards.pop(i)


@registered_plugin
class AwardsPlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("AwardsPlugin")

        self.html_ids = {
            "Award Name": self.identifier + "_award_name",
            "Award Recipient": self.identifier + "_award_recipient",
            "Award Body": self.identifier + "_award_body",
            "Old Award Key": self.identifier + "_old_key",
            "Confirm Delete": self.identifier + "_confirm_delete",
        }

        self.exports = [
            Export(
                "awards_add",
                "Awards -> Create",
                self.ask_award_create_or_update,
                self.answer_award_create_or_update,
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

    def gather_awards(self) -> List[Tuple[str, str]]:
        return [
            (award.render_name(), award.get_key()) for award in self.AWARDS_DATABASE.awards
        ]

    def ask_award_create_or_update(self, award_key: str = "") -> List[HTMLComponent]:
        award = self.AWARDS_DATABASE.get(award_key) if award_key else None
        components = [
            AwardNameEntry(
                identifier=self.html_ids["Award Name"],
                title="Name of the award",
                default=award.render_name() if award else "",
                suggestions=SUGGESTED_AWARDS,
            ),
            DefaultNamedSmallTextbox(
                identifier=self.html_ids["Award Recipient"],
                title="Recipient of the award",
                default=award.winner if award else "",
            ),
            HtmlEntry(
                identifier=self.html_ids["Award Body"],
                title="Award body",
                default=(award.body if award else "") + AWARD_BODY_INSTRUCTIONS,
            )
        ]
        if award:
            components.append(HiddenTextbox(self.html_ids["Old Award Key"], award.get_key()))
        return components

    def answer_award_create_or_update(self, html_response) -> List[HTMLComponent]:
        award_name = Award.parse_name(html_response[self.html_ids["Award Name"]])
        award_winner = html_response[self.html_ids["Award Recipient"]]
        award_body = HTML_COMMENT_PATTERN.sub("", html_response[self.html_ids["Award Body"]]).strip()

        old_key = html_response.get(self.html_ids["Old Award Key"])
        components = []
        if old_key:
            award = self.AWARDS_DATABASE.get(old_key)
            award.name = award_name
            award.winner = award_winner
            award.body = award_body
            components.append(Label("[AWARDS] Updated award."))
        else:
            self.AWARDS_DATABASE.add(Award(
                name=award_name,
                winner=award_winner,
                body=award_body,
            ))
            components.append(Label("[AWARDS] Added award."))
        self.AWARDS_DATABASE.save()
        return components

    def ask_award_delete(self, award_key: str) -> List[HTMLComponent]:
        award = self.AWARDS_DATABASE.get(award_key)
        return [
            Table(
                [("Name", award.render_name()),
                 ("Recipient", award.winner),
                 ("Body", award.body)]
            ),
            # We don't need to be particularly careful about deleting awards,
            # hence use a Checkbox rather than a DigitsChallenge
            Checkbox(
                self.html_ids["Confirm Delete"],
                "Delete the above award?"
            ),
            HiddenTextbox(self.html_ids["Old Award Key"], award_key),
        ]

    def answer_award_delete(self, html_response) -> List[HTMLComponent]:
        if html_response[self.html_ids["Confirm Delete"]]:
            self.AWARDS_DATABASE.delete(html_response[self.html_ids["Old Award Key"]])
            return [Label("[AWARDS] Deleted award.")]
        else:
            return [Label("[AWARDS] Did not delete award.")]
