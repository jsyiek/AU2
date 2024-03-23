from html import escape

from AU2.html_components import HTMLComponent


class NamedSmallTextbox(HTMLComponent):
    name: str = "NamedSmallTextbox"

    def __init__(self, identifier: str, title: str, type_="text"):
        self.title = escape(title)
        self.identifier = escape(identifier)
        self.uniqueStr = self.get_unique_str()
        self.type_ = type_
        super().__init__()

    def _representation(self) -> str:
        return f"""
            <label for="{self.identifier}">{self.title}</label>
            <input type="{self.type_}" id="{self.identifier}"><br><br>
        """
