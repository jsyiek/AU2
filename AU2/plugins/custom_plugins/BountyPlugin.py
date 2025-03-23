import os
from typing import List

from AU2 import ROOT_DIR
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model.Event import Event
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.custom_plugins.PageGeneratorPlugin import render_event, DAY_TEMPLATE, weeks_and_days_to_str, date_to_weeks_and_days
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.CompetencyManager import CompetencyManager
from AU2.plugins.util.WantedManager import WantedManager
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.date_utils import get_now_dt
from AU2.plugins.util.game import get_game_start


BOUNTIES_PAGE_TEMPLATE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "bounties.html"), "r", encoding="utf-8",
          errors="ignore") as F:
    BOUNTIES_PAGE_TEMPLATE = F.read()


@registered_plugin
class BountyPlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("BountyPlugin")

        self.html_ids = {
            "bounty_event": self.identifier + "_bounty_event"
        }

    def on_event_request_create(self, *_) -> List[HTMLComponent]:
        return [
            Checkbox(
                identifier=self.html_ids["bounty_event"],
                title="Is this a bounty?",
                checked=False
            )
        ]

    def on_event_request_update(self, e: Event, *_) -> List[HTMLComponent]:
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
        return [Label("[BOUNTY] Success")]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        is_bounty = htmlResponse[self.html_ids["bounty_event"]]
        e.pluginState.setdefault(self.identifier, {})["bounty"] = is_bounty
        return [Label("[BOUNTY] Success")]

    def on_page_generate(self, _) -> List[HTMLComponent]:
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda event: event.datetime)

        start_datetime = get_game_start()
        start_date = start_datetime.date()

        competency_manager = CompetencyManager(start_datetime)
        death_manager = DeathManager(perma_death=True)
        wanted_manager = WantedManager()

        bounties_for_day = {}

        for e in events:
            wanted_manager.add_event(e)
            competency_manager.add_event(e)
            death_manager.add_event(e)

            # only render bounties
            if not e.pluginState.get(self.identifier, {}).get("bounty", False):
                continue

            event_text, _ = render_event(
                e,
                competency_manager=competency_manager,
                wanted_manager=wanted_manager,
                death_manager=death_manager
            )
            days_since_start, _, _ = date_to_weeks_and_days(start_date, e.datetime.date())
            bounties_for_day.setdefault(days_since_start, []).append(event_text)

        bounty_days = []
        for (d, event_list) in bounties_for_day.items():
            bounty_days.append(
                DAY_TEMPLATE.format(
                    DATE=weeks_and_days_to_str(start_date, 1, d),
                    EVENTS="".join(event_list)
                )
            )

        bounty_content = "".join(bounty_days)
        if bounty_content == "":
            bounty_content = "<p>Ah, no bounties yet.</p>"

        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "bounties.html"), "w+", encoding="utf-8") as F:
            F.write(
                BOUNTIES_PAGE_TEMPLATE.format(
                    CONTENT=bounty_content,
                    YEAR=str(get_now_dt().year)
                )
            )
        return [Label("[BOUNTY] Success!")]
