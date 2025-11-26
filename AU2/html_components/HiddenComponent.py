from typing import Generic, TypeVar
from AU2.html_components import HTMLComponent

T = TypeVar("T")


class HiddenComponent(HTMLComponent, Generic[T]):
    noInteraction: bool = True

    def __init__(self, identifier: str, default: T):
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        super().__init__()
