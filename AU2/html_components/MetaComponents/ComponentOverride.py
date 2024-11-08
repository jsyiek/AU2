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
            replace_with: HTMLComponent,
            replacement_effects: Callable[[HTMLComponent, HTMLComponent], None] = lambda *args: None):
        """
        Args:
            overrides: identifier of component to override
            replace_with: component to replace with
            replacement_effects: arbitrary function that takes in (old_component, replace_with)
        """
        self.overrides = overrides
        self.replace_with = replace_with
        self.uniqueStr = self.get_unique_str()  # TODO: refactor to snake case
        self.replacement_effects = replacement_effects
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
