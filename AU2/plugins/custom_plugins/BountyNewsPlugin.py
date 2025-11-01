from typing import List

from AU2 import ROOT_DIR
from AU2.database.model.Event import Event
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.date_utils import get_now_dt
from AU2.plugins.util.render_utils import Chapter, render_all_events


BOUNTIES_PAGE_TEMPLATE: str
with open(ROOT_DIR / "plugins" / "custom_plugins" / "html_templates" / "bounty-news.html",
           "r", encoding="utf-8", errors="ignore") as F:
    BOUNTIES_PAGE_TEMPLATE = F.read()


@registered_plugin
class BountyNewsPlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("BountyNewsPlugin")

        self.html_ids = {
            "bounty_event": self.identifier + "_bounty_event"
        }

    def on_event_request_create(self) -> List[HTMLComponent]:
        return [
            Checkbox(
                identifier=self.html_ids["bounty_event"],
                title="Is this a bounty?",
                checked=False
            )
        ]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        return [
            Checkbox(
                identifier=self.html_ids["bounty_event"],
                title="Is this a bounty?",
                checked=e.pluginState.get(self.identifier, {}).get("bounty", False)
            )
        ]

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        is_bounty = htmlResponse[self.html_ids["bounty_event"]]
        e.pluginState.setdefault(self.identifier, {})["bounty"] = is_bounty
        return [Label("[BOUNTY NEWS] Success")]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        is_bounty = htmlResponse[self.html_ids["bounty_event"]]
        e.pluginState.setdefault(self.identifier, {})["bounty"] = is_bounty
        return [Label("[BOUNTY NEWS] Success")]

    def on_page_generate(self, _) -> List[HTMLComponent]:
        BOUNTY_CHAPTER = Chapter("bounty-news", "Bounties")
        _, bounty_chapters = render_all_events(
            # note: this will include hidden events,
            # to allow bounties to be set to appear only on the bounties page and not main news
            page_allocator=lambda e: BOUNTY_CHAPTER if e.pluginState.get(self.identifier, {}).get("bounty", False) else None
        )
        bounty_content = "".join(bounty_chapters.get(BOUNTY_CHAPTER, tuple())) or "<p>Ah, no bounties yet.</p>"
        with open(WEBPAGE_WRITE_LOCATION / "bounty-news.html", "w+", encoding="utf-8") as F:
            F.write(
                BOUNTIES_PAGE_TEMPLATE.format(
                    CONTENT=bounty_content,
                    YEAR=str(get_now_dt().year)
                )
            )
        return [Label("[BOUNTY NEWS] Success!")]
