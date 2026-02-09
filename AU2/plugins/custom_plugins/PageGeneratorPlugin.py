import os

from typing import List

from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.FloatEntry import FloatEntry
from AU2.html_components.SimpleComponents.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.util.game import get_game_end
from AU2.plugins.util.navbar import NavbarEntry
from AU2.plugins.util.render_utils import Chapter, default_page_allocator, DEFAULT_REAL_NAME_BRIGHTNESS, \
    generate_news_pages, get_real_name_brightness, PageAllocatorData, set_real_name_brightness

@registered_plugin
class PageGeneratorPlugin(AbstractPlugin):
    def __init__(self):
        # unique identifier for the plugin
        self.identifier = "PageGeneratorPlugin"
        super().__init__(self.identifier)

        self.html_ids = {
            "Hidden": self.identifier + "_hidden",
            "Brightness": self.identifier + "_brightness",
            "Duel Page?": self.identifier + "_duel_page",
        }

        self.plugin_state = {
            "HIDDEN": "hidden_event",
            "Duel Page?": "duel_page",
        }

        self.exports = []

        self.config_exports = [
            ConfigExport(
                "page_generator_plugin_real_name_brightness",
                "PageGeneratorPlugin -> Adjust brightness of real names on news pages",
                self.ask_set_real_name_brightness,
                self.answer_set_real_name_brightness
            ),
        ]

    def ask_set_real_name_brightness(self) -> List[HTMLComponent]:
        return [
            Label("Below you can set the % brightness of real names relative to pseudonyms on news pages."),
            Label("If brightness = 100%, real names are rendered the same colour as pseudonyms."),
            Label("If brightness < 100%, real names are rendered darker than pseudonyms."),
            Label("If brightness > 100%, real names are rendered lighter than pseudonyms "
                  "(this is not recommended as it tends to be hard to read)."),
            Label("If brightness <= 0%, real names are rendered in black."),
            Label(f"The default, recommended brightness is {DEFAULT_REAL_NAME_BRIGHTNESS :.0%}."),
            FloatEntry(
                self.html_ids["Brightness"],
                "Set % brightness for real names",
                100 * get_real_name_brightness()
            )
        ]

    def answer_set_real_name_brightness(self, html_response) -> List[HTMLComponent]:
        set_real_name_brightness(html_response[self.html_ids["Brightness"]] / 100)
        return [Label(f"[NEWS PAGE GENERATOR] Successfully set real name brightness to {get_real_name_brightness():.0%}!")]

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

    def on_data_hook(self, hook: str, data):
        if hook == "page_allocator":
            data: PageAllocatorData

            # Hide hidden events.
            HIDDEN_PAGE_PRIORITY = 10000
            if data.event.pluginState.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False):
                data.chapter = None
                data.priority = HIDDEN_PAGE_PRIORITY

            # Assign events after game end to a separate Duel page, if so configured
            DUEL_PAGE_PRIORITY = 2
            if (GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get(self.plugin_state["Duel Page?"], False)
                    and data.priority < DUEL_PAGE_PRIORITY):
                end = get_game_end()
                if end and end < data.event.datetime:
                    data.chapter = Chapter("duel", "The Duel")
                    data.priority = DUEL_PAGE_PRIORITY

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

    def on_page_generate(self, htmlResponse, navbar_entry) -> List[HTMLComponent]:
        duel_page = False
        if self.html_ids["Duel Page?"] in htmlResponse:
            duel_page = htmlResponse[self.html_ids["Duel Page?"]]
            GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {})[self.plugin_state["Duel Page?"]] = duel_page

        end = get_game_end() if duel_page else None

        DUEL_CHAPTER = Chapter("The Duel", NavbarEntry("duel.html", "The Duel", float("Inf")))

        generate_news_pages(
            headlines_path="head.html",
            # note: need to check default allocation first in case event is hidden!
            page_allocator=lambda e: (DUEL_CHAPTER
                                      if (default := default_page_allocator(e))
                                         and end is not None
                                         and end < e.datetime
                                      else default),
            news_list_path="news-list.html",
        )

        return [Label("[NEWS PAGE GENERATOR] Successfully generated the story!")]
