import datetime
import zlib
from html import escape
from typing import List, Tuple

from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import Event, Assassin
from AU2.html_components import HTMLComponent
from AU2.html_components.AssassinDependentFloatEntry import AssassinDependentFloatEntry
from AU2.html_components.AssassinDependentSelector import AssassinDependentSelector
from AU2.html_components.Checkbox import Checkbox
from AU2.html_components.Dependency import Dependency
from AU2.html_components.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin
from AU2.plugins.CorePlugin import registered_plugin

DAY_TEMPLATE = """<h3 xmlns="">{DATE}</h3> {EVENTS}"""

EVENT_TEMPLATE = """    <div xmlns="" class="event"><hr/><span id="{ID}">
  [{TIME}]
   <span class="headline">{HEADLINE}</span></span><hr/>
   {REPORTS}
    </div>
"""

REPORT_TEMPLATE = """<div class="report">{PSEUDONYM} reports: <br/>
<div class="indent"><div class="colourunknown"><p>{REPORT}</p></div></div></div>
"""

PSEUDONYM_TEMPLATE = """<b style="color:{COLOR}">{PSEUDONYM}</b>"""

HEX_COLS = [
    '#B1AB8A', '#75C49C', '#7BA5A2', '#B0B477', '#B6CDBC',
    '#EC7DD2', '#B964EB', '#758FAC', '#EEABF2', '#6892B0',
    '#D9FBBF', '#D4A66A', '#8E7CE6', '#7CCC64', '#95B7F5',
    '#FF81EA', '#EB82D4', '#E89F6E', '#98A0CD', '#ACC6D0'
]

DEAD_COLS = [
    '#A9756C', '#A688BF', '#A34595'
]


@registered_plugin
class PageGeneratorPlugin(AbstractPlugin):
    def __init__(self):
        # unique identifier for the plugin
        self.identifier = "PageGeneratorPlugin"
        super().__init__(self.identifier)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def process_all_events(self, _: List[Event]) -> List[HTMLComponent]:
        return []

    def on_event_request_create(self) -> List[HTMLComponent]:
        return [
            Checkbox(self.html_ids["Hidden"], "Hidden: if 'Yes' then do not display on website", checked=False),
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentFloatEntry(
                        identifier=self.html_ids["Points"],
                        title="Points: select players to manually adjust",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym"
                    )
                ]
            )
        ]

    def on_event_create(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState[self.identifier][self.plugin_state["POINTS"]] = \
            htmlResponse[self.html_ids["Points"]]
        e.pluginState[self.identifier][self.plugin_state["HIDDEN"]] = htmlResponse[self.html_ids["Hidden"]]

        return [Label("[PAGE GENERATOR] Success!")]

    def on_event_request_update(self, e: Event) -> List[HTMLComponent]:
        points = e.pluginState.get(self.identifier, {}).get(self.plugin_state["POINTS"], None)
        hidden = e.pluginState.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False)
        return [
            Checkbox(self.html_ids["Hidden"], "Hidden: if 'Yes' then do not display on website", checked=hidden),
            Dependency(
                dependentOn="CorePlugin_assassin_pseudonym",
                htmlComponents=[
                    AssassinDependentFloatEntry(
                        identifier=self.html_ids["Points"],
                        title="Points: select players to manually adjust",
                        pseudonym_list_identifier="CorePlugin_assassin_pseudonym",
                        default=points
                    )
                ]
            )
        ]

    def get_color(self, pseudonym: str, dead: bool=False) -> str:
        ind = zlib.adler32(pseudonym.encode(encoding="utf-32"))
        if dead:
            return DEAD_COLS[ind % len(DEAD_COLS)]
        return HEX_COLS[ind % len(HEX_COLS)]

    def substitute_pseudonyms(self, string: str, main_pseudonym: str, assassin: Assassin, color: str) -> str:
        id_ = assassin._secret_id
        string = string.replace(f"[P{id_}]", PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=escape(main_pseudonym)))
        for i in range(len(assassin.pseudonyms)):
            string = string.replace(f"[P{id_}_{i}]", PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=escape(assassin.pseudonyms[i])))
        string = string.replace(f"[D{id_}]",
                                    " AKA ".join(PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=escape(p)) for p in assassin.pseudonyms))
        string = string.replace(f"[N{id_}]",
                                    PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=escape(assassin.real_name)))
        return string

    def ask_generate_the_story(self) -> List[HTMLComponent]:
        return [Label("[PAGE GENERATOR] Preparing...")]

    def answer_generate_the_story(self, _) -> List[HTMLComponent]:
        events = list(EVENTS_DATABASE.events.values())
        events.sort(key=lambda e: e.datetime)
        events_for_chapter = {}
        start_date: datetime.datetime = None
        for e in events:
            if e.headline.startswith("GAME START") and e.pluginState.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False):
                start_date = e.datetime.date()
                break
        else:
            return [Label(
                "[PAGE GENERATOR] Could not determine game start. Create an event with headline GAME START and make it hidden.")]

        news_week_length = 7

        # maps chapter (news week) to day-of-week to list of reports
        # this is 1-indexed (week 1 is first week of game)
        events_for_chapter = {0: {}}
        week_count = 1

        for e in events:
            # skip hidden events
            # this is purely rendering
            if e.pluginState.get(self.identifier, {}).get(self.plugin_state["HIDDEN"], False):
                continue

            days_since_start = (e.datetime.date() - start_date).days
            week = days_since_start // 7
            day = days_since_start % 7
            if days_since_start < 0:
                days_since_start = -1
            elif days_since_start > max(CHAPTERS):
                days_since_start = max(CHAPTERS)
            events_for_chapter.setdefault(days_since_start, [])

            is_dead: List[str] = []
            for (_, victim) in e.kills:
                is_dead.append(victim)

            headline = e.headline

            reports = {(playerID, pseudonymID): report for (playerID, pseudonymID, report) in e.reports}

            for (assassin, pseudonym_index) in e.assassins.items():
                assassin_model = ASSASSINS_DATABASE.get(assassin)
                pseudonym = assassin_model.pseudonyms[pseudonym_index]
                color = self.get_color(pseudonym, assassin in is_dead)
                headline = self.substitute_pseudonyms(headline, pseudonym, assassin_model, color)

                for (k, r) in reports.items():
                    reports[k] = self.substitute_pseudonyms(r, pseudonym, assassin_model, color)

            # For his May Week, Thomas O'Hare wants the reports to render *without* the pseudonym/real_name
            report_list = []
            for (_, r) in reports.items():
                report_list.append(
                    # not escaping r so we can have HTML in the reports
                    # I hope you know what you're doing, Thomas!
                    REPORT_TEMPLATE.format(TEXT=r)
                )
            report_text = "<br><br>".join(report_list)
            event_text = EVENT_TEMPLATE.format(HEADLINE=headline, REPORTS=report_text)
            events_for_chapter[days_since_start].append(event_text)

        all_chapters = []
        for (day, event_list) in events_for_chapter.items():
            all_event_text = "<br>".join(event_list)
            chapter_text = DAY_EVENTS_TEMPLATE.format(
                # again not escaping for same reason
                CHAPTER=CHAPTERS[day],
                EVENTS=all_event_text
            )
            all_chapters.append(chapter_text)

        all_chapter_text = """<hr style="width:30%;text-align:center"></hr>""".join(all_chapters)
        quote = self.get_current_quote()
        webpage_text = THE_STORY_TEMPLATE.format(QUOTE=quote, DAYS=all_chapter_text)

        path = os.path.join(WEBPAGE_WRITE_LOCATION, "head.html")

        with open(path, "w+") as F:
            F.write(webpage_text)

        return [Label("[MAFIA] Successfully generated the story!")]

    def on_event_update(self, e: Event, htmlResponse) -> List[HTMLComponent]:
        e.pluginState[self.identifier][self.plugin_state["POINTS"]] = \
            htmlResponse[self.html_ids["Points"]]
        e.pluginState[self.identifier][self.plugin_state["HIDDEN"]] = htmlResponse[self.html_ids["Hidden"]]

        return [Label("[PAGE GENERATOR] Success!")]

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
