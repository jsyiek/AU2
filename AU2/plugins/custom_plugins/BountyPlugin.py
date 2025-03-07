import os
from dataclasses import dataclass
from typing import Dict, Any, List

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.html_components import HTMLComponent
from AU2.html_components.MetaComponents.Searchable import Searchable
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown
from AU2.html_components.SimpleComponents.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.date_utils import get_now_dt

TABLE_TEMPLATE = """
<table xmlns="" class="playerlist">
    <tr><th>TARGET</th><th>BOUNTY POSTER</th><th>ALLEGED TRANSGRESSION</th><th>REWARD</th></tr>
    {ROWS}
</table>
"""

ROW_TEMPLATE = """
<tr><td>{TARGET_NAME}</td><td>{PLACER_NAME}</td><td>{CRIME}</td><td>{REWARD}</td></tr>
"""

BOUNTIES_PAGE_TEMPLATE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "bounties.html"), "r", encoding="utf-8",
          errors="ignore") as F:
    BOUNTIES_PAGE_TEMPLATE = F.read()


@dataclass
class Bounty:
    identifier: str = ""
    target_id: str = ""
    placer_id: str = ""
    crime: str = ""
    reward: str = ""
    active: bool = True

    @staticmethod
    def from_dict(identifier: str, d: Dict[str, Any]):
        b = Bounty(
            identifier,
            d.get("target_id", ""),
            d.get("placer_id", ""),
            d.get("crime", "Nothing...?"),
            d.get("reward", "Nothing...?"),
            d.get("active", False)
        )
        b.make_identifier()
        return b

    def make_identifier(self):
        self.identifier = self.identifier or f"({GENERIC_STATE_DATABASE.get_unique_str()}) {self.target_id[0:8]} from {self.placer_id[0:8]}"

    def to_dict(self):
        return {
            "target_id": self.target_id,
            "placer_id": self.placer_id,
            "crime": self.crime,
            "reward": self.reward,
            "active": self.active
        }


@registered_plugin
class BountyPlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("BountyPlugin")

        self.html_ids = {
            "identifier": "identifier",
            "target": "target_id",
            "placer": "placer_id",
            "crime": "crime",
            "reward": "reward",
            "active": "active"
        }

        self.exports = [
            Export(
                "bounty_add_bounty",
                "Bounties -> Add bounty",
                self.ask_create_bounty,
                self.answer_set_bounty
            ),
            Export(
                "bounty_update_bounty",
                "Bounties -> Update bounty",
                self.ask_update_bounty,
                self.answer_set_bounty,
                (self.get_bounty_ids,)
            )
        ]

    def ask_create_bounty(self):
        return self._bounty_questions()

    def ask_update_bounty(self, bounty_id: str):
        return self._bounty_questions(self._read_bounty(bounty_id))

    def answer_set_bounty(self, html_response):
        bounties_dict = GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {}).setdefault("bounties", {})
        bounty = Bounty.from_dict(html_response[self.html_ids["identifier"]], html_response)
        bounties_dict[bounty.identifier] = bounty.to_dict()
        return [Label("[BOUNTY] Success!")]

    def _bounty_questions(self, default=Bounty()):

        def setter(component, options):
            component.options = options
            if component.selected and component.selected not in options:
                component.options.append(component.selected)

        return [
            HiddenTextbox(
                identifier=self.html_ids["identifier"],
                default=default.identifier
            ),
            Searchable(
                InputWithDropDown(
                    identifier=self.html_ids["target"],
                    title="Who is the bounty on?",
                    options=ASSASSINS_DATABASE.get_identifiers(),
                    selected=default.target_id
                ),
                title="Who is the bounty on? (Search)",
                accessor=lambda i: i.options,
                setter=setter
            ),
            Searchable(
                InputWithDropDown(
                    identifier=self.html_ids["placer"],
                    title="Who is placing the bounty?",
                    options=ASSASSINS_DATABASE.get_identifiers(),
                    selected=default.placer_id
                ),
                title="Who is placing the bounty? (Search)",
                accessor=lambda i: i.options,
                setter=setter
            ),
            DefaultNamedSmallTextbox(
                identifier=self.html_ids["crime"],
                title="What is the crime?",
                default=default.crime
            ),
            DefaultNamedSmallTextbox(
                identifier=self.html_ids["reward"],
                title="What is the reward?",
                default=default.reward
            ),
            Checkbox(
                identifier=self.html_ids["active"],
                title="Should the bounty be posted on the website?",
                checked=True
            )
        ]

    def on_page_generate(self, _) -> List[HTMLComponent]:
        bounties_dict = GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {}).setdefault("bounties", {})
        bounties = [Bounty.from_dict(identifier, bounties_dict[identifier]) for identifier in bounties_dict]
        bounties = [b for b in bounties if b.active]

        table_str = "<p>Ah, no bounties yet.</p>"

        if bounties:
            rows = []
            for b in bounties:
                rows.append(
                    ROW_TEMPLATE.format(
                        TARGET_NAME=ASSASSINS_DATABASE.assassins[b.target_id].real_name,
                        PLACER_NAME=ASSASSINS_DATABASE.assassins[b.placer_id].real_name,
                        CRIME=b.crime,
                        REWARD=b.reward
                    )
                )
            table_str = TABLE_TEMPLATE.format(ROWS="\n".join(rows))

        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "bounties.html"), "w+", encoding="utf-8") as F:
            F.write(
                BOUNTIES_PAGE_TEMPLATE.format(
                    YEAR=get_now_dt().year,
                    TABLE_OPTIONAL=table_str
                )
            )
        return [Label("[BOUNTY] Success!")]

    def _read_bounty(self, bounty_id: str):
        return Bounty.from_dict(
            bounty_id,
            GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {}).setdefault("bounties", {}).setdefault(
                bounty_id, {})
        )

    def get_bounty_ids(self):
        return list(GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {}).setdefault("bounties", {}).keys())
