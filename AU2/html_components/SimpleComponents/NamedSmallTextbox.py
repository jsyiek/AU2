from html import escape

from AU2.html_components import HTMLComponent


class NamedSmallTextbox(HTMLComponent):
    name: str = "NamedSmallTextbox"

    # TODO: convert `DefaultNamedSmallTextbox`s to `NamedSmallTextbox`s
    def __init__(self, identifier: str, title: str, default: str = "", type_="text"):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        self.type_ = type_
        super().__init__()

    def _representation(self) -> str:
        return f"""
            <label for="{self.identifier}">{self.title}</label>
            <input type="{self.type_}" id="{self.identifier}"><br><br>
        """
