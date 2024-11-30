import dataclasses
from typing import List

from AU2.database.model import Event
from AU2.html_components import HTMLComponent


@dataclasses.dataclass
class Suggestion:
    """
    Dataclass to store information about sanity check changes
    """

    # Explanation of the change to be displayed to user.
    # Keep this short.
    explanation: str

    # Identifier that uniquely identifies the change to the SanityCheck.
    identifier: str


class SanityCheck:
    """
    Represents a check that must be performed before pages generate.
    """
    identifier: str

    def has_marked(self, e: Event) -> bool:
        """
        Returns True if e has been marked by this sanity check.
        """
        return self.identifier in e.pluginState.get("sanity_checks", [])

    def mark(self, e: Event):
        """
        Marks an event as having been reviewed by this SanityCheck.
        Marked events are not reviewed in subsequent iterations.

        Arguments:
            e: Event to mark
        """
        e.pluginState.setdefault("sanity_checks", []).append(self.identifier)

    def suggest_event_fixes(self, e: Event) -> List[Suggestion]:
        """
        Returns a list of suggestions for fixes to an event.

        Arguments:
            e: Event to suggest changes for

        Returns:
            List of suggestions
        """
        raise NotImplementedError()

    def fix_event(self, e: Event, suggestion_ids: List[str]) -> List[HTMLComponent]:
        """
        After a user has confirmed one or more changes are wanted, this function
        executes the changes

        Arguments:
            e: Event to fix
            suggestion_ids: List of suggestion identifiers that should be implemented

        Returns:
            List of HTML components to display to user.
        """
        raise NotImplementedError()
