from typing import Any, Dict, List, Sequence, Tuple, Union

from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown


class Branch(HTMLComponent):
    """
    MetaComponent to display different subcomponents depending on the selection.

    Attributes:
        identifier (str): component identifier
        title (str): text to display at the initial selection
        options (List[str | Tuple[str, Any]]): branch options to display to the user. Each option may either be a tuple
            of (display text, internal value), or just a str which is equivalent to having that value for both display
            text and internal value.
        components_map (Dict[Any, HTMLComponent]): a mapping from options to a list of subcomponents to render if the
            option is selected
        selected (Any, optional): the (internal value of the) default selection

    Response format: in the HTMLResponse, this component's `identifier` will map to the selected option's internal value,
        whilest the subcomponents will have their own entries under their own identifiers.
    """

    name = "Branch"

    def __init__(self, identifier: str, title: str, options: List[Union[str, Tuple[str, Any]]], components_map: Dict[Any, Sequence[HTMLComponent]],
                 selected: Any = None):
        self.title = title
        self.identifier = identifier
        self.options = options
        self.components_map = components_map
        self.selected = selected
        super().__init__()

    def as_InputWithDropdown(self) -> InputWithDropDown:
        """
        Produces an `InputWithDropdown` component that can render the branch selection part of this component.
        """
        return InputWithDropDown(
            identifier=self.identifier,
            title=self.title,
            options=self.options,
            selected=self.selected
        )
