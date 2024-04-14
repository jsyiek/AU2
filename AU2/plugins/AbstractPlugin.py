from typing import List

from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent


def only_when_enabled(func):
    def decorator(self, *args, **kwargs):
        if self.enabled:
            return func(self, *args, **kwargs)
        return []

    return decorator


class Export:
    """
    Represents an HTML callback
    """

    def __init__(self, identifier: str, display_name: str, ask, answer):
        """
        :param identifier: internal identifier for the callback
        :param display_name: html-visible display name
        :param ask: function that generates a list of HTML components
        :param answer: function that takes a dictionary of arg -> str and actions the output.
        """
        self.identifier = identifier
        self.display_name = display_name
        self.ask = ask
        self.answer = answer


# You must define and export this variable
EXPORT_PLUGIN = None


class AbstractPlugin:
    def __init__(self, identifier: str):
        # unique identifier for the plugin
        self.identifier = identifier
        self.enabled = True
        self.exports: List[Export] = []

    def _dump_state(self):
        """
        I don't recommend your plugin dumps any state, although some plugins in rare cases
        might want to. State doesn't play well with deleted events!
        :return:
        """
        return

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    @only_when_enabled
    def process_all_events(self, _: List[Event]) -> List[HTMLComponent]:
        return []

    @only_when_enabled
    def on_event_update(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return []

    @only_when_enabled
    def on_event_create(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return []

    @only_when_enabled
    def on_event_delete(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return []

    @only_when_enabled
    def on_assassin_request_create(self) -> List[HTMLComponent]:
        return []

    @only_when_enabled
    def on_assassin_update(self, _: Assassin, htmlResponse) -> List[HTMLComponent]:
        return []

    @only_when_enabled
    def on_assassin_create(self, _: Assassin, htmlResponse) -> List[HTMLComponent]:
        return []

    @only_when_enabled
    def on_assassin_delete(self, _: Assassin, htmlResponse) -> List[HTMLComponent]:
        return []

