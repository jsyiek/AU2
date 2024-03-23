from typing import List

from AU2.html_components import HTMLComponent


class InputWithDropDown(HTMLComponent):

    name = "InputWithDropDown"

    def __init__(self, identifier: str, title: str, options: List[str]):
        self.title = title
        self.identifier = identifier
        self.options = options
        super().__init__()

    def _representation(self) -> str:
        list_options = []
        for option in self.options:
            list_options.append(f'<option value="{option}">')

        options = "\n".join(list_options)
        list_name = self.title + self.identifier
        return f"""
        <label>{self.title}
            <input list="{list_name}" id="{self.identifier}" /></label>
            <datalist id="{list_name}">
            {options}
            </datalist>
        """
