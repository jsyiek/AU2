from typing import Callable

from AU2.html_components import HTMLComponent


class ComponentOverride(HTMLComponent):
    """
    At representation time, suppose there is one element with identifier A and any number
    of overrides targeting A. The resultant render will replace the original element with
    any ONE of the overrides.

    This guarantee is intentionally non-deterministic to simplify implementation logic for
    overrides.
    """

    name: str = "Override"

    def __init__(
            self,
            overrides: str,
            replacement_factory: Callable[[HTMLComponent], HTMLComponent] = lambda c: c):
        """
        Args:
            overrides: identifier of component to override
            replacement_factory: produces the replacement for the component specified by `overrides`.
                (Takes old component as an argument).
        """
        self.overrides = overrides
        self.replacement_factory = replacement_factory
        self.uniqueStr = self.get_unique_str()  # TODO: refactor to snake case
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
