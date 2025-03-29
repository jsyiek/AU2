from typing import List, Callable, Tuple, Union

from AU2.html_components import HTMLComponent

class ForEach(HTMLComponent):
    """
    Component which allows the user to select a subset of `options`,
    then for each of these options renders a series of subcompents to give input for each option in turn.
    This is used to replace all the DependentComponents.
    """
    name: str = "ForEach"

    def __init__(self,
                 identifier: str,
                 title: str,
                 options: List[Union[str, Tuple[str, str]]],
                 subcomponents_factory: Callable[[str], List[HTMLComponent]],
                 default_selection: List[str] = [],
                 explanation: List[str] = []):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.options = options
        self.default_selection = default_selection
        self.subcomponents_factory = subcomponents_factory
        self.explanation = explanation
        super().__init__()

    def _representation(self) -> str:
        # Note: in the HTML implementation,
        # generate all the subcomponents "in advance" using
        raise NotImplementedError()
