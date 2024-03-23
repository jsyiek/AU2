from typing import List

from AU2.database.model import Event, Assassin


def only_when_enabled(func):
    def decorator(self, *args, **kwargs):
        if self.enabled:
            func(self, *args, **kwargs)

    return decorator


# You must define and export this variable
EXPORT_PLUGIN = None


class AbstractPlugin:
    def __init__(self, identifier: str):
        # unique identifier for the plugin
        self.identifier = identifier
        self.enabled = True

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
    def process_all_events(self, _: List[Event]):
        return

    @only_when_enabled
    def on_event_update(self, _: Event, htmlResponse):
        return

    @only_when_enabled
    def on_event_create(self, _: Event, htmlResponse):
        return

    @only_when_enabled
    def on_event_delete(self, _: Event, htmlResponse):
        return

    @only_when_enabled
    def on_assassin_request_create(self):
        return

    @only_when_enabled
    def on_assassin_update(self, _: Assassin, htmlResponse):
        return

    @only_when_enabled
    def on_assassin_create(self, _: Assassin, htmlResponse):
        return

    @only_when_enabled
    def on_assassin_delete(self, _: Assassin, htmlResponse):
        return

