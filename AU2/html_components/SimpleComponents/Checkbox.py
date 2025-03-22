from html import escape

from AU2.html_components import HTMLComponent


class Checkbox(HTMLComponent):
    name: str = "Checkbox"

    def __init__(self, identifier: str, title: str, checked: bool=False, *, force_default: bool=False):

        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.checked = checked
        self.force_default = force_default
        super().__init__()

    def _representation(self) -> str:
        checked = "checked"
        emp = ""
        return f"""
            <label for="{self.identifier}">{self.title}</label>
            <input type="checkbox" id="{self.identifier}" name="exampleCheckbox" {checked if self.checked else emp}>
        """
