import os

from typing import List

from AU2 import ROOT_DIR
from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.FloatEntry import FloatEntry
from AU2.html_components.SimpleComponents.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, ConfigExport
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.date_utils import get_now_dt
from AU2.plugins.util.render_utils import DEFAULT_REAL_NAME_BRIGHTNESS, get_real_name_brightness, render_all_events, \
    set_real_name_brightness

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
            "Brightness": self.identifier + "_brightness",
        }

        self.plugin_state = {
            "HIDDEN": "hidden_event"
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

    def on_assassin_request_create(self) -> List[HTMLComponent]:
        return []

    def on_assassin_create(self, _: Assassin, htmlResponse) -> List[HTMLComponent]:
        return []

    def on_assassin_request_update(self, _: Assassin) -> List[HTMLComponent]:
        return []

    def on_assassin_update(self, _: Assassin, htmlResponse) -> List[HTMLComponent]:
        return []
