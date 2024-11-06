from typing import List

from AU2.html_components import HTMLComponent


class Dependency(HTMLComponent):
    """
    At representation time, will ensure the relevant component is present
    Merges all dependencies for the same identifier into the same Dependency class
    and ensures the required dependency is at the front.

    dependentOn: the identifier of the HTMLComponent depended on
    """

    name: str = "Dependency"

    def __init__(self, dependentOn: str, htmlComponents: List[HTMLComponent]):
        self.dependentOn = dependentOn
        self.uniqueStr = self.get_unique_str()
        self.htmlComponents = htmlComponents
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
