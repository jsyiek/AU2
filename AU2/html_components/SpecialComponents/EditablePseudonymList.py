from html import escape
from typing import Iterable
from collections import namedtuple

from AU2.html_components import HTMLComponent

PseudonymData = namedtuple("PseudonymData", ["text", "valid_from"])
ListUpdates = namedtuple("PseudonymUpdates", ["edited", "new_values", "deleted_indices"])

class EditablePseudonymList(HTMLComponent):
    name: str = "EditablePseudonymList"

    def __init__(self, identifier: str, title: str, values: Iterable[PseudonymData]):
        self.title = escape(title)
        self.identifier = escape(identifier)
        self.uniqueStr = self.get_unique_str()
        # values should be an iterable of PseudonymData types
        self.values = [a for a in values]
        super().__init__()

    def _representation(self) -> str:
        # TODO: create a HTML version of this component.
        #       Broadly, it should be a list of textboxes with the list values given,
        #       with the option to add new textboxes.
        raise NotImplementedError()
