from html import escape

from AU2.html_components import HTMLComponent


class HiddenTextbox(HTMLComponent):
    name: str = "HiddenTextbox"

    def __init__(self, identifier: str, default: str):
        self.identifier = escape(identifier)
        self.uniqueStr = self.get_unique_str()
        self.default = escape(default)
        super().__init__()

    def _representation(self) -> str:
        return f"""
            <input type="hidden" id="{self.identifier}" value="{self.default}">
        """
