from re import Pattern
from typing import Sequence, Union

from AU2.html_components import HTMLComponent

class RegexValidatedEntry(HTMLComponent):
    """An HTML Component that validates text input using a regex pattern.
    Also supports autocomplete suggestions."""

    name: str = "RegexValidatedEntry"

    def __init__(self, identifier: str, title: str, regex: Union[str, Pattern], error_message: str = "Invalid input",
                 default: str = "", suggestions: Sequence[str] = ()):
        self.title = title
        self.identifier = identifier
        self.default = default
        self.regex = regex
        self.error_message = error_message
        self.suggestions = suggestions
        super().__init__()

    def _representation(self) -> str:
        # note: in a HTML + JS implementation fronted, regex.pattern can be used to extract the original regex string
        raise NotImplemented()
