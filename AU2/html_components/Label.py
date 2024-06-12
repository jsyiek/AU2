from typing import List

from AU2.html_components import HTMLComponent


class Label(HTMLComponent):

    name = "Label"

    def __init__(self, title: str):
        self.identifier = "Label" # needed for compatibility but not strictly relevant
        self.title = title
        super().__init__()

    def _representation(self) -> str:
        return f"<label>{self.title}</label>"
