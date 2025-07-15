from typing import List, Dict

from AU2.html_components import HTMLComponent


class AssassinDependentInputWithDropDown(HTMLComponent):
    """
    Component which has the user select a subset of the players in an event, and choose an option for each one.
    E.g., to change a player's team.
    """

    name: str = "AssassinDependentInputWithDropDown"

    def __init__(self, pseudonym_list_identifier: str, identifier: str, title: str, options: List[str], default: Dict[str, str]={}):
        self.pseudonym_list_identifier = pseudonym_list_identifier
        self.title = title
        self.identifier = identifier
        self.options = options
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
