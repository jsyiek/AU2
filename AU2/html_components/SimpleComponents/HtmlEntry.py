from AU2.html_components import HTMLComponent


class HtmlEntry(HTMLComponent):
    """
    A component which validates HTML,
    but only if the input includes the HTML specifier.
    """
    name: str = "HtmlEntry"

    def __init__(self, identifier: str, title: str, default: str = ""):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        raise NotImplemented()
