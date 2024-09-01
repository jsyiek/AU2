import datetime
import os
import zlib
from html import escape
from typing import List, Tuple

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.Checkbox import Checkbox
from AU2.html_components.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.CompetencyManager import CompetencyManager
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.game import get_game_start

DAY_TEMPLATE = """<h3 xmlns="">{DATE}</h3> {EVENTS}"""


EVENT_TEMPLATE = """<div xmlns="" class="event"><hr/><span id="{ID}">
  [{TIME}]
   <span class="headline">{HEADLINE}</span></span><hr/>
   {REPORTS}
    </div>
"""


REPORT_TEMPLATE = """<div class="report">{PSEUDONYM} reports: <br/>
<div class="indent"><div style="color:{REPORT_COLOR}"><p>{REPORT}</p></div></div></div>
"""


PSEUDONYM_TEMPLATE = """<b style="color:{COLOR}">{PSEUDONYM}</b>"""


NEWS_TEMPLATE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "news.html"), "r") as F:
    NEWS_TEMPLATE = F.read()


HEX_COLS = [
    '#B1AB8A', '#75C49C', '#7BA5A2', '#B0B477', '#B6CDBC',
    '#EC7DD2', '#B964EB', '#758FAC', '#EEABF2', '#6892B0',
    '#D9FBBF', '#D4A66A', '#8E7CE6', '#7CCC64', '#95B7F5',
    '#FF81EA', '#EB82D4', '#E89F6E', '#98A0CD', '#ACC6D0'
]


DEAD_COLS = [
    '#A9756C', '#A688BF', '#A34595'
]


INCO_COLORS = [
    "#FFC0CB",  # Light Pink
    "#FFB6C1",  # Light Pink 2
    "#FF69B4",  # Hot Pink
    "#FF1493",  # Deep Pink
    "#DB7093",  # Pale Violet Red
    "#FF5A77",  # Radical Red
    "#FF6EB4",  # Hot Pink 3
    "#FF82AB",  # Light Pink 3
    "#FF007F",  # Bright Pink
    "#FF85B2"   # Ultra Pink
]

HEAD_HEADLINE_TEMPLATE = """
    <div xmlns="" class="event">
  [<a href="news{NUMBER}.html#{ID}">{TIME}</a>]
   <span class="headline">{HEADLINE}</span><br/></div>"""

HEAD_DAY_TEMPLATE = """<h3 xmlns="">{DATE}</h3> {HEADLINES}"""

HEAD_TEMPLATE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "head.html"), "r") as F:
    HEAD_TEMPLATE = F.read()

HARDCODED_COLORS = {
    "The Dragon Queen": "#19268A",
    "Water Ghost": "#606060",
    "Valheru": "#03FCEC",
    "Vendetta": "#B920DB"
}


def weeks_and_days_to_str(start: datetime.datetime, week: int, day: int) -> str:
    """
    Converts a 1-indexed week and a 0-indexed day into a string for news webpage

    It might seem counterintuitive to make the days and weeks different indexing.
    This is because week 0 news takes place the week before the game starts.
    This is usually rendered as a bounty.
    """
    return (start + datetime.timedelta(days=day, weeks=week-1)).strftime("%A, %d %B")


def datetime_to_time_str(event_time: datetime.datetime) -> str:
    """
    Returns a formatted timestamp suitable for the news.
    """
    return event_time.strftime("%I:%M %p")


def soft_escape(string: str) -> str:
    """
    Escapes only if not prefixed by <!--HTML-->
    """

    # umpires may regret allowing this
    # supposing you are a clever player who has found this and the umpire does not know...
    # please spare the umpire any headaches
    # and remember that code injection without explicit consent is illegal (CMA sxn 2/3)
    if not string.startswith("<!--HTML-->"):
        return escape(string)
    return string


@registered_plugin
class PageGeneratorPlugin(AbstractPlugin):
    def __init__(self):
        # unique identifier for the plugin
        self.identifier = "PageGeneratorPlugin"
        super().__init__(self.identifier)

        self.html_ids = {
            "Hidden": self.identifier + "_hidden",
        }

        self.plugin_state = {
            "HIDDEN": "hidden_event"
        }

        self.exports = []

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def process_all_events(self, _: List[Event]) -> List[HTMLComponent]:
        return []

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

    def get_color(self, pseudonym: str, dead: bool=False, incompetent: bool=False) -> str:
        ind = zlib.adler32(pseudonym.encode(encoding="utf-32"))
        if dead:
            return DEAD_COLS[ind % len(DEAD_COLS)]
        if incompetent:
            return INCO_COLORS[ind % len(INCO_COLORS)]
        if pseudonym in HARDCODED_COLORS:
            return HARDCODED_COLORS[pseudonym]
        return HEX_COLS[ind % len(HEX_COLS)]

    def substitute_pseudonyms(self, string: str, main_pseudonym: str, assassin: Assassin, color: str) -> str:
        id_ = assassin._secret_id
        string = string.replace(f"[P{id_}]", PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(main_pseudonym)))
        for i in range(len(assassin.pseudonyms)):
            string = string.replace(f"[P{id_}_{i}]", PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(assassin.pseudonyms[i])))
        string = string.replace(f"[D{id_}]",
                                    " AKA ".join(PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(p)) for p in assassin.pseudonyms))
        string = string.replace(f"[N{id_}]",
                                    PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(assassin.real_name)))
        return string

    def on_page_request_generate(self) -> List[HTMLComponent]:
        return [Label("[NEWS PAGE GENERATOR] Preparing...")]

    def on_page_generate(self, _) -> List[HTMLComponent]:
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda event: event.datetime)
        start_datetime: datetime.datetime = get_game_start()
        start_date: datetime.date = start_datetime.date()

        # maps chapter (news week) to day-of-week to list of reports
        # this is 1-indexed (week 1 is first week of game)
        # days are 0-indexed (fun, huh?)
        events_for_chapter = {0: {}}
        headlines_for_day = {}
        competency_manager = CompetencyManager(start_datetime)
        death_manager = DeathManager(perma_death=True)

        for e in events:
            # skip hidden events
            # this is purely rendering
            if e.pluginState.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False):
                continue

            competency_manager.add_event(e)
            death_manager.add_event(e)

            headline = e.headline

            reports = {(playerID, pseudonymID): soft_escape(report) for (playerID, pseudonymID, report) in e.reports}

            for (assassin, pseudonym_index) in e.assassins.items():
                assassin_model = ASSASSINS_DATABASE.get(assassin)
                pseudonym = assassin_model.pseudonyms[pseudonym_index]

                # TODO: Wanted coloring
                # TODO: Incompetent coloring
                # TODO: Police coloring
                color = self.get_color(
                    pseudonym,
                    dead=death_manager.is_dead(assassin_model),
                    incompetent=competency_manager.is_inco_at(assassin_model, e.datetime)
                )
                headline = self.substitute_pseudonyms(headline, pseudonym, assassin_model, color)

                for (k, r) in reports.items():
                    reports[k] = self.substitute_pseudonyms(r, pseudonym, assassin_model, color)

            report_list = []
            for ((assassin, pseudonym_index), r) in reports.items():
                # Umpires must tell AU to NOT escape HTML
                # If they tell it not to, they do so at their own risk. Make sure you know what you want to do!
                # TODO: Initialize the default report template with some helpful HTML tips, such as this fact
                assassin_model = ASSASSINS_DATABASE.get(assassin)
                pseudonym = assassin_model.pseudonyms[pseudonym_index]
                color = self.get_color(
                    pseudonym,
                    dead=death_manager.is_dead(assassin_model),
                    incompetent=competency_manager.is_inco_at(assassin_model, e.datetime)
                )

                painted_pseudonym = PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(pseudonym))

                report_list.append(
                    REPORT_TEMPLATE.format(PSEUDONYM=painted_pseudonym, REPORT_COLOR=color, REPORT=r)
                )
            days_since_start = (e.datetime.date() - start_date).days

            week = days_since_start // 7 + 1
            day = days_since_start % 7
            if week < 0:
                week = 0
                day = days_since_start + 7
            events_for_chapter.setdefault(week, {})

            report_text = "".join(report_list)
            time_str = datetime_to_time_str(e.datetime)
            event_text = EVENT_TEMPLATE.format(
                ID=e._Event__secret_id,
                TIME=time_str,
                HEADLINE=headline,
                REPORTS=report_text
            )
            events_for_chapter[week].setdefault(day, []).append(event_text)

            headline_text = HEAD_HEADLINE_TEMPLATE.format(
                NUMBER=f"{week:02}",
                ID=e._Event__secret_id,
                TIME=time_str,
                HEADLINE=headline
            )
            headlines_for_day.setdefault(days_since_start, []).append(headline_text)

        weeks = {}
        for (w, d_dict) in events_for_chapter.items():
            outs = []
            for (d, events_list) in d_dict.items():
                all_event_text = "".join(events_list)
                day_text = DAY_TEMPLATE.format(
                    # again not escaping for same reason
                    DATE=weeks_and_days_to_str(start_date, w, d),
                    EVENTS=all_event_text
                )
                outs.append(day_text)
            weeks[w] = NEWS_TEMPLATE.format(
                N=w,
                DAYS="".join(outs),
                YEAR=str(datetime.datetime.now().year)
            )

        for w in weeks:
            path = os.path.join(WEBPAGE_WRITE_LOCATION, f"news{w:02}.html")

            with open(path, "w+") as F:
                F.write(weeks[w])

        head_days = []
        for (d, headlines_list) in headlines_for_day.items():
            head_days.append(
                HEAD_DAY_TEMPLATE.format(
                    DATE=weeks_and_days_to_str(start_date, 1, d),
                    HEADLINES="".join(headlines_list)
                )
            )

        head_page_text = HEAD_TEMPLATE.format(
            CONTENT="".join(head_days),
            YEAR=str(datetime.datetime.now().year)
        )
        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "head.html"), "w+") as F:
            F.write(head_page_text)

        return [Label("[NEWS PAGE GENERATOR] Successfully generated the story!")]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState.setdefault(self.identifier, {})
        e.pluginState[self.identifier][self.plugin_state["HIDDEN"]] = htmlResponse[self.html_ids["Hidden"]]

        return [Label("[NEWS PAGE GENERATOR] Success!")]

    def on_event_delete(self, _: Event, htmlResponse) -> List[HTMLComponent]:
        return []

    def on_assassin_request_create(self) -> List[HTMLComponent]:
        return []

    def on_assassin_create(self, _: Assassin, htmlResponse) -> List[HTMLComponent]:
        return []

    def on_assassin_request_update(self, _: Assassin) -> List[HTMLComponent]:
        return []

    def on_assassin_update(self, _: Assassin, htmlResponse) -> List[HTMLComponent]:
        return []
