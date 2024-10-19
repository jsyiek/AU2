from typing import List

from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.html_components.AssassinDependentSelector import AssassinDependentSelector
from AU2.html_components.Dependency import Dependency
from AU2.html_components.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin
from AU2.plugins.CorePlugin import registered_plugin


@registered_plugin
class AttemptPlugin(AbstractPlugin):
    """
    NEW TO AU2
    Provides a way of recording Attempts/Assists in events
    Essentially denoting an active player who did not manage to secure a kill, while ignoring passive/defensive players
    These can be hooked onto by other plugins, to automate and speedup other umpiring tasks that used to be painful
    """
    def __init__(self):
        super().__init__("AttemptPlugin")

        self.event_html_ids = {
            "Attempts": self.identifier + "_attempts"
        }

    def on_event_request_create(self) -> List[HTMLComponent]:
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentSelector(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.event_html_ids["Attempts"],
                        title="ATTEMPTS: Select players who made an attempt or assist",
                    )]
            )
        ]

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState[self.identifier] = htmlResponse[self.event_html_ids["Attempts"]]
        return [Label("[ATTEMPTS] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        return [
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentSelector(
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        identifier=self.event_html_ids["Attempts"],
                        title="ATTEMPTS: Select players who made an attempt or assist",
                        default=e.pluginState.get(self.identifier, {}),
                    )]
            )
        ]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState[self.identifier] = htmlResponse[self.event_html_ids["Attempts"]]
        return [Label("[ATTEMPTS] Success!")]
