from typing import List, Dict, Any, Callable, TypeVar, Tuple

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
                 options: List[Tuple[str, T_]],
                 defaults: Dict[T_, Dict[str, S_]],
                 subcomponents_factory: Callable[[T_, Dict[T_, Dict[str, S_]]], List[HTMLComponent]]):
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.options = options
        self.defaults = defaults
        self.subcomponents_factory = subcomponents_factory
        super().__init__()

    def _representation(self) -> str:
        # Note: in the HTML implementation,
        # generate all the subcomponents "in advance" using
        raise NotImplementedError()
