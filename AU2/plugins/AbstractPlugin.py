from typing import List

from AU2.database.model import Event


class AbstractPlugin:
    def __init__(self, identifier: str):
        # unique identifier for the plugin
        self.identifier = identifier

    def _dump_state(self):
        """
        I don't recommend your plugin dumps any state, although some plugins in rare cases
        might want to. State doesn't play well with deleted events!
        :return:
        """
        return

    def process_all_events(self, _: List[Event]):
        return

    def on_event_update(self, _: Event, htmlResponse):
        return

    def on_event_create(self, _: Event, htmlResponse):
        return

    def on_event_delete(self, _: Event, htmlResponse):
        return

    def on_assassin_update(self, _: Event, htmlResponse):
        return

    def on_assassin_create(self, _: Event, htmlResponse):
        return

    def on_assassin_delete(self, _: Event, htmlResponse):
        return
