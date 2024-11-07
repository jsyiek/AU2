from html import escape

from AU2.html_components import HTMLComponent


class LargeTextEntry(HTMLComponent):
    name: str = "LargeTextEntry"

    def __init__(self, identifier: str, title: str, default: str=""):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()

    def _representation(self) -> str:
        return f"""
            <label for="{self.identifier}">{self.title}</label>
            <input type="{self.type_}" id="{self.identifier}"><br><br>
        """
