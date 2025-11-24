import os

from typing import List

from AU2 import ROOT_DIR
from AU2.database.model import Assassin, Event
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.date_utils import get_now_dt
from AU2.plugins.util.render_utils import get_color_real_names, render_all_events, set_color_real_names

NEWS_TEMPLATE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "news.html"), "r", encoding="utf-8", errors="ignore") as F:
    NEWS_TEMPLATE = F.read()

HEAD_TEMPLATE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "head.html"), "r", encoding="utf-8", errors="ignore") as F:
    HEAD_TEMPLATE = F.read()


@registered_plugin
class PageGeneratorPlugin(AbstractPlugin):
    def __init__(self):
        # unique identifier for the plugin
        self.identifier = "PageGeneratorPlugin"
        super().__init__(self.identifier)

        self.html_ids = {
            "Hidden": self.identifier + "_hidden",
            "Colour real names?": self.identifier + "_color_real_names"
        }

        self.plugin_state = {
            "HIDDEN": "hidden_event"
        }

        self.exports = []

        self.config_exports = [
            ConfigExport(
                "page_generator_plugin_colour_real_names",
                "PageGeneratorPlugin -> Toggle colouring real names",
                self.ask_set_color_real_names,
                self.answer_set_color_real_names,
            ),
        ]

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

    def on_page_request_generate(self) -> List[HTMLComponent]:
        return []

    def on_page_generate(self, _) -> List[HTMLComponent]:
        headline_days, weeks = render_all_events(
            exclude=lambda e: e.pluginState.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False)
        )

        for w in weeks:
            path = os.path.join(WEBPAGE_WRITE_LOCATION, f"news{w:02}.html")
            week_page_text = NEWS_TEMPLATE.format(
                N=w,
                DAYS="".join(weeks[w]),
                YEAR=str(get_now_dt().year)
            )
            with open(path, "w+", encoding="utf-8", errors="ignore") as F:
                F.write(week_page_text)

        head_page_text = HEAD_TEMPLATE.format(
            CONTENT="".join(headline_days),
            YEAR=str(get_now_dt().year)
        )
        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "head.html"), "w+", encoding="utf-8", errors="ignore") as F:
            F.write(head_page_text)

        return [Label("[NEWS PAGE GENERATOR] Successfully generated the story!")]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})
        e.pluginState[self.identifier][self.plugin_state["HIDDEN"]] = htmlResponse[self.html_ids["Hidden"]]

        return [Label("[NEWS PAGE GENERATOR] Success!")]

    def on_request_setup_game(self, game_type: str) -> List[HTMLComponent]:
        return [
            *self.ask_set_color_real_names()
        ]

    def on_setup_game(self, html_response) -> List[HTMLComponent]:
        return [
            *self.answer_set_color_real_names(html_response)
        ]

    def ask_set_color_real_names(self) -> List[HTMLComponent]:
        return [
            Checkbox(
                self.html_ids["Colour real names?"],
                "Colour real names in headlines?",
                get_color_real_names()
            )
        ]

    def answer_set_color_real_names(self, html_response) -> List[HTMLComponent]:
        newval = html_response[self.html_ids["Colour real names?"]]
        set_color_real_names(newval)
        return [Label(f"[NEWS PAGE GENERATOR] {'En' if newval else 'Dis'}abled colouring of real names.")]
