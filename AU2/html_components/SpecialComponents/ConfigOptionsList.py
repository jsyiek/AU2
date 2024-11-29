from typing import List

from AU2.html_components import HTMLComponent
from AU2.plugins.AbstractPlugin import ConfigExport


class ConfigOptionsList(HTMLComponent):
    """
    Special component used for the plugin config selector,
    so that we can deal with DangerousConfigOptions correctly.
    How these are rendered specifically is left up to the front-end; inquirer_cli simply colours them red
    """

    name = "ConfigOptionsList"

    def __init__(self, identifier: str, title: str, config_options: List[ConfigExport]):
        """
        Args:
            identifier: internal identifier
            title: visible label for the component
            config_options: list of ConfigExports to display. The front-end will deal with rendering
                `DangerousConfigExport`s correctly.
        """
        self.identifier = identifier
        self.title = title
        self.config_options = config_options
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
