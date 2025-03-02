from AU2.html_components import HTMLComponent


class HiddenJSON(HTMLComponent):
    name: str = "HiddenJSON"
    noInteraction: bool = True

    def __init__(self, identifier: str, default: dict):
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        # When implementing this as HTML,
        # the dict `default` would be serialised as JSON to render this component.
        raise NotImplemented()
