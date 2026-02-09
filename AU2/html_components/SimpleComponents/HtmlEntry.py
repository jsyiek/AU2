from AU2.html_components import HTMLComponent


class HtmlEntry(HTMLComponent):
    """
    A component which validates HTML.
    """
    name: str = "HtmlEntry"

    def __init__(self, identifier: str, title: str, default: str = "", soft: bool = False, short: bool = False):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        self.soft = soft
        self.short = short
        super().__init__()

    def _representation(self) -> str:
        raise NotImplemented()
