from typing import List, Callable

from AU2.html_components import HTMLComponent


class Searchable(HTMLComponent):
    """
    Allows arbitrary searching over any list based HTML component
    """

    def __init__(
            self,
            component: HTMLComponent,
            title: str,
            accessor: Callable[[HTMLComponent], List[str]] = None,
            setter: Callable[[HTMLComponent, List[str]], None] = None):
        """
        Args:
            component: Component to make searchable
            title: Message to display
            accessor: Retrieves the list of options from the component
            setter: Given an object of the same type, sets the options appropriately.
        """
        self.identifier = component.identifier
        self.component = component
        self.title = title
        self.accessor = accessor
        self.setter = setter
        super().__init__()
