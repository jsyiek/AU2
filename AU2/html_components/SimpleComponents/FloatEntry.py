from AU2.html_components import HTMLComponent


class FloatEntry(HTMLComponent):
    name: str = "IntegerEntry"

    def __init__(self, identifier: str, title: str, default: int):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
