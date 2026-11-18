from AU2.html_components import HTMLComponent


class OptionalIntegerEntry(HTMLComponent):
    name: str = "OptionalIntegerEntry"

    def __init__(self, identifier: str, title: str, default: int):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
