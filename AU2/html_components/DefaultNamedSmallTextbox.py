from html import escape

from AU2.html_components import HTMLComponent


class DefaultNamedSmallTextbox(HTMLComponent):
    name: str = "DefaultNamedSmallTextbox"

    def __init__(self, identifier: str, title: str, default: str, type_="text"):
        self.title = escape(title)
        self.identifier = escape(identifier)
        self.uniqueStr = self.get_unique_str()
        self.type_ = type_
        self.default = escape(default)
        super().__init__()

    def _representation(self) -> str:
        return f"""
            <label for="{self.identifier}">{self.title}</label>
            <input type="{self.type_}" id="{self.identifier}" value="{self.default}"><br><br>
        """
