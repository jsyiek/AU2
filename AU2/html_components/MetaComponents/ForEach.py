from typing import List, Dict, Callable, TypeVar, Tuple, Union

from AU2.html_components import HTMLComponent

T_ = TypeVar("T_")
S_ = TypeVar("S_")

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
                 options: List[Union[str, Tuple[str, T_]]],
                 subcomponents_factory: Callable[[T_, S_], List[HTMLComponent]],
                 defaults: Dict[T_, S_] = {},
                 explanation: List[str] = []):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.options = options
        self.defaults = defaults
        self.subcomponents_factory = subcomponents_factory
        self.explanation = explanation
        super().__init__()

    def _representation(self) -> str:
        # Note: in the HTML implementation,
        # generate all the subcomponents "in advance" using
        raise NotImplementedError()
