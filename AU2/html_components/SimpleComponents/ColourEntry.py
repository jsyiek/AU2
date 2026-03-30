from typing import Optional

from AU2.html_components import HTMLComponent
from AU2.plugins.util.render_utils import RGBValues


class ColourEntry(HTMLComponent):
    """Component for entering colours.
    Response value is of form (int, int, int), representing the colour rgb values,
    or None (only if `optional` is set to True).

    Attributes:
        identifier (str): key under which to put the response to this component
        title (str): text labelling the component for the user
        default (Optional[int, int, int]): the default colour, in RGB values, or None for no default
        optional (bool): whether to allow a 'null' value
    """
    name: str = "ColourEntry"

    def __init__(self, identifier: str, title: str, default: Optional[RGBValues], optional: bool = False):
        self.title = title
        self.identifier = identifier
        self.default = default
        self.optional = optional
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
