from typing import Optional
from AU2.html_components import HTMLComponent


class FloatEntry(HTMLComponent):
    name: str = "FloatEntry"

    def __init__(self, identifier: str, title: str, default: Optional[float], optional: bool = False,):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        self.optional = optional
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
