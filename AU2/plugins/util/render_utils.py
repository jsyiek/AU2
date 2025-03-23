import datetime
import re
import zlib
import itertools

from typing import Callable, Dict, List

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import Event, Assassin
from AU2.plugins.util.CompetencyManager import CompetencyManager
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.WantedManager import WantedManager
from AU2.plugins.util.date_utils import datetime_to_time_str, date_to_weeks_and_days, get_now_dt, weeks_and_days_to_str
from AU2.plugins.util.game import get_game_start, soft_escape

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

# TODO: make this configurable?
HARDCODED_COLORS = {
    "The Dragon Queen": "#19268A",
    "Water Ghost": "#606060",
    "Valheru": "#03FCEC",
    "Vendetta": "#B920DB"
}

HEX_COLS = [
    '#00A6A3', '#26CCC8', '#008B8A', '#B69C1F',
    '#D1B135', '#5B836E', '#7A9E83', '#00822b',
    '#00A563', '#FFA44D', '#CC6C1E', '#37b717',
    '#27B91E', '#1F9E1A', '#3DC74E', '#00c6c3',
    '#b7a020', '#637777', '#f28110'
]

DEAD_COLS = [
    "#A9756C", "#A688BF", "#A34595", "#8C5D56",
    "#8E7A9E", "#873A80", "#B0978F", "#9C8FA8",
]


INCO_COLS = [
    "#FF33CC", "#FF6699", "#FF3399",
    "#E63FAE", "#D94F9F", "#FF80BF",
]

POLICE_COLS = [
    "#4D54E3", "#7433FF", "#3B6BD4",
    "#0066CC", "#3366B2", "#4159E0",
]

DEAD_POLICE_COLS = [
    "#000066"
]

CORRUPT_POLICE_COLS = [
    "#9999CC"
]

WANTED_COLS = [
    "#ff0033", "#cc3333", "#ff3300"
]


HEAD_HEADLINE_TEMPLATE = """
    <div xmlns="" class="event">
  [<a href="{URL}">{TIME}</a>]
   <span class="headline">{HEADLINE}</span><br/></div>"""

HEAD_DAY_TEMPLATE = """<h3 xmlns="">{DATE}</h3> {HEADLINES}"""

FORMAT_SPECIFIER_REGEX = r"\[[D,P,N]([0-9]+)(?:_([0-9]+))?\]"


def event_url(e: Event) -> str:
    """
    Generates the (relative) url pointing to this event's appearance on the news pages
    """
    week = date_to_weeks_and_days(get_game_start().date(), e.datetime.date()).week
    return f"news{week:02}.html#{e._Event__secret_id}"


def get_color(pseudonym: str,
              dead: bool = False,
              incompetent: bool = False,
              is_police: bool = False,
              is_wanted: bool = False) -> str:
    ind = zlib.adler32(pseudonym.encode(encoding="utf-8"))
    if is_wanted:
        if is_police:
            return CORRUPT_POLICE_COLS[ind % len(CORRUPT_POLICE_COLS)]
        return WANTED_COLS[ind % len(WANTED_COLS)]
    if dead:
        if is_police:
            return DEAD_POLICE_COLS[ind % len(DEAD_POLICE_COLS)]
        return DEAD_COLS[ind % len(DEAD_COLS)]
    if incompetent:
        return INCO_COLS[ind % len(INCO_COLS)]
    if pseudonym in HARDCODED_COLORS:
        return HARDCODED_COLORS[pseudonym]
    if is_police:
        return POLICE_COLS[ind % len(POLICE_COLS)]
    return HEX_COLS[ind % len(HEX_COLS)]


def substitute_pseudonyms(string: str, main_pseudonym: str, assassin: Assassin, color: str, dt: datetime.datetime = get_now_dt()) -> str:
    id_ = assassin._secret_id
    string = string.replace(f"[P{id_}]", PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(main_pseudonym)))
    for i in range(len(assassin.pseudonyms)):
        string = string.replace(f"[P{id_}_{i}]", PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(assassin.get_pseudonym(i))))
    string = string.replace(f"[D{id_}]",
                            " AKA ".join(PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(p)) for p in assassin.pseudonyms_until(dt)))
    string = string.replace(f"[N{id_}]",
                            PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(assassin.real_name)))
    return string


def render_headline_and_reports(e: Event,
                                death_manager: DeathManager,
                                competency_manager: CompetencyManager,
                                wanted_manager: WantedManager) -> (str, List[str]):
    headline = e.headline

    reports = {(playerID, pseudonymID): soft_escape(report) for (playerID, pseudonymID, report) in
               e.reports}

    candidate_pseudonyms = []

    texts_to_search = [r for r in itertools.chain((headline,), reports.values())]

    for r in texts_to_search:
        for match in re.findall(FORMAT_SPECIFIER_REGEX, r):
            assassin_secret_id = int(match[0])

            assassin_model: Assassin
            for a in ASSASSINS_DATABASE.assassins.values():
                if int(a._secret_id) == assassin_secret_id:
                    assassin_model = a
                    break
            else:
                continue

            if any(c[0].identifier == assassin_model.identifier for c in candidate_pseudonyms):
                continue

            pseudonym_index = int(match[1] or e.assassins.get(assassin_model.identifier, 0))
            pseudonym = assassin_model.get_pseudonym(pseudonym_index)

            color = get_color(
                pseudonym,
                dead=death_manager.is_dead(assassin_model),
                incompetent=competency_manager.is_inco_at(assassin_model, e.datetime),
                is_police=assassin_model.is_police,
                is_wanted=wanted_manager.is_player_wanted(assassin_model.identifier, time=e.datetime)
            )

            candidate_pseudonyms.append((assassin_model, pseudonym, color))

    for (assassin_model, pseudonym, color) in candidate_pseudonyms:
        headline = substitute_pseudonyms(headline, pseudonym, assassin_model, color, e.datetime)
        for (k, r) in reports.items():
            reports[k] = substitute_pseudonyms(r, pseudonym, assassin_model, color, e.datetime)

    return headline, reports


def render_event(e: Event,
                 death_manager: DeathManager,
                 competency_manager: CompetencyManager,
                 wanted_manager: WantedManager) -> (str, str):
    """
    Renders the full HTML for the event, including headline and reports
    Also gives the HTML rendering of the headline for the headlines page.
    """
    headline, reports = render_headline_and_reports(
        e,
        death_manager=death_manager,
        competency_manager=competency_manager,
        wanted_manager=wanted_manager
    )
    report_list = []
    for ((assassin, pseudonym_index), r) in reports.items():
        # Umpires must tell AU to NOT escape HTML
        # If they tell it not to, they do so at their own risk. Make sure you know what you want to do!
        # TODO: Initialize the default report template with some helpful HTML tips, such as this fact
        assassin_model = ASSASSINS_DATABASE.get(assassin)
        pseudonym = assassin_model.get_pseudonym(pseudonym_index)
        color = get_color(
            pseudonym,
            dead=death_manager.is_dead(assassin_model),
            incompetent=competency_manager.is_inco_at(assassin_model, e.datetime),
            is_police=assassin_model.is_police,
            is_wanted=wanted_manager.is_player_wanted(assassin_model.identifier, time=e.datetime)
        )

        painted_pseudonym = PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(pseudonym))

        report_list.append(
            REPORT_TEMPLATE.format(PSEUDONYM=painted_pseudonym, REPORT_COLOR=color, REPORT=r)
        )

    report_text = "".join(report_list)
    time_str = datetime_to_time_str(e.datetime)
    event_text = EVENT_TEMPLATE.format(
        ID=e._Event__secret_id,
        TIME=time_str,
        HEADLINE=headline,
        REPORTS=report_text
    )
    headline_text = HEAD_HEADLINE_TEMPLATE.format(
        URL=event_url(e),
        TIME=time_str,
        HEADLINE=headline
    )
    return event_text, headline_text


def render_all_events(exclude: Callable[[Event], bool]) -> (List[str], Dict[int, List[str]]):
    """
    Produces a rendering of all events not excluded by `exclude`.

    Args:
        exclude: a function taking an Event as input and returning a boolean for whether or not it should be rendered.

    Returns:
        A tuple of: a list of strings where each element is the HTML rendering of one day's headlines, and a dict
            mapping week numbers to a list of strings where each element is the HTML rendering of one day's reports.
    """
    events = list(EVENTS_DATABASE.events.values())
    events.sort(key=lambda event: event.datetime)
    start_datetime = get_game_start()
    start_date = start_datetime.date()

    # maps chapter (news week) to day-of-week to list of reports
    # this is 1-indexed (week 1 is first week of game)
    # days are 0-indexed (fun, huh?)
    events_for_chapter = {0: {}}
    headlines_for_day = {}
    competency_manager = CompetencyManager(start_datetime)
    death_manager = DeathManager(perma_death=True)
    wanted_manager = WantedManager()

    for e in events:
        # don't skip adding hidden events to managers, in case a player dies in a hidden event, etc.
        wanted_manager.add_event(e)
        competency_manager.add_event(e)
        death_manager.add_event(e)

        if exclude(e):
            continue

        days_since_start, week, day = date_to_weeks_and_days(start_date, e.datetime.date())
        events_for_chapter.setdefault(week, {})

        event_text, headline_text = render_event(
            e,
            death_manager=death_manager,
            competency_manager=competency_manager,
            wanted_manager=wanted_manager
        )

        events_for_chapter[week].setdefault(day, []).append(event_text)
        headlines_for_day.setdefault(days_since_start, []).append(headline_text)

    weeks = {}
    for (w, d_dict) in events_for_chapter.items():
        outs = []
        for (d, events_list) in d_dict.items():
            all_event_text = "".join(events_list)
            day_text = DAY_TEMPLATE.format(
                DATE=weeks_and_days_to_str(start_date, w, d),
                EVENTS=all_event_text
            )
            outs.append(day_text)
        weeks[w] = outs

    head_days = []
    for (d, headlines_list) in headlines_for_day.items():
        head_days.append(
            HEAD_DAY_TEMPLATE.format(
                DATE=weeks_and_days_to_str(start_date, 1, d),
                HEADLINES="".join(headlines_list)
            )
        )

    return head_days, weeks