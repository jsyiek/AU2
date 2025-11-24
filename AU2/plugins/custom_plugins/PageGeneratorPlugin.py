import os

from typing import List

from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.util.game import get_game_end
from AU2.plugins.util.render_utils import Chapter, default_page_allocator, generate_news_pages

@registered_plugin
class PageGeneratorPlugin(AbstractPlugin):
    def __init__(self):
        # unique identifier for the plugin
        self.identifier = "PageGeneratorPlugin"
        super().__init__(self.identifier)

        self.html_ids = {
            "Hidden": self.identifier + "_hidden",
            "Duel Page?": self.identifier + "_duel_page"
        }

        self.plugin_state = {
            "HIDDEN": "hidden_event",
            "Duel Page?": "duel_page",
        }

        self.exports = []

    def on_event_request_create(self) -> List[HTMLComponent]:
        return [
            Checkbox(self.html_ids["Hidden"], "Hidden: if 'Yes' then do not display on website", checked=False),
        ]

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})
        e.pluginState[self.identifier][self.plugin_state["HIDDEN"]] = htmlResponse[self.html_ids["Hidden"]]

        return [Label("[NEWS PAGE GENERATOR] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        hidden = e.pluginState.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False)
        return [
            Checkbox(self.html_ids["Hidden"], "Hidden: if 'Yes' then do not display on website", checked=hidden),
        ]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})
        e.pluginState[self.identifier][self.plugin_state["HIDDEN"]] = htmlResponse[self.html_ids["Hidden"]]

        return [Label("[NEWS PAGE GENERATOR] Success!")]

    def on_page_request_generate(self) -> List[HTMLComponent]:
        components = []
        # determine whether any visible events occur after game end,
        # then ask whether these should be placed on a separate "duel" page
        game_end = get_game_end()
        if game_end and any(
                e.datetime > game_end for e in EVENTS_DATABASE.events.values()
                if not e.pluginState.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False)
        ):
            components.append(Checkbox(self.html_ids["Duel Page?"],
                                       "Events detected after end of game. Put these on separate duel page?",
                                       GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get(self.plugin_state["Duel Page?"], False)))
        return components

    def on_page_generate(self, htmlResponse) -> List[HTMLComponent]:
        duel_page = False
        if self.html_ids["Duel Page?"] in htmlResponse:
            duel_page = htmlResponse[self.html_ids["Duel Page?"]]
            GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {})[self.plugin_state["Duel Page?"]] = duel_page

        end = get_game_end() if duel_page else None

        DUEL_CHAPTER = Chapter("duel", "The Duel", "The Duel", float("Inf"))

        generate_news_pages(
            headlines_path="head.html",
            page_allocator=lambda e: DUEL_CHAPTER if end and end < e.datetime else default_page_allocator(e),
            news_list_path="news-list.html",
        )

        return [Label("[NEWS PAGE GENERATOR] Successfully generated the story!")]
