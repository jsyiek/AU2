from html import escape

from AU2.html_components import HTMLComponent


class NamedSmallTextbox(HTMLComponent):
    name: str = "NamedSmallTextbox"

    def __init__(self, title: str, identifier: str):
        self.title = escape(title)
        self.identifier = escape(identifier)
        self.uniqueStr = self.get_unique_str()
        super().__init__()

    def _representation(self) -> str:
        return f"""
            <label for="{self.identifier}">{self.title}</label>
            <input type="text" id="{self.identifier}"><br><br>
        """
