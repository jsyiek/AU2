import datetime
import itertools
import markdown
import re
from typing import Callable, Dict, List, NamedTuple, Optional, Protocol, Sequence, Tuple

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model import Event, Assassin
from AU2.plugins.AbstractPlugin import NavbarEntry
from AU2.plugins.util.CompetencyManager import CompetencyManager
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.WantedManager import WantedManager
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.date_utils import datetime_to_time_str, date_to_weeks_and_days, get_now_dt
from AU2.plugins.util.game import get_game_start, soft_escape, HTML_REPORT_PREFIX

NEWS_TEMPLATE: str
with open(ROOT_DIR / "plugins" / "custom_plugins" / "html_templates" / "news.html", "r", encoding="utf-8", errors="ignore") as F:
    NEWS_TEMPLATE = F.read()

HEAD_TEMPLATE: str
with open(ROOT_DIR / "plugins" / "custom_plugins" / "html_templates" / "head.html", "r", encoding="utf-8", errors="ignore") as F:
    HEAD_TEMPLATE = F.read()

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

CITY_WATCH_COLS = [
    "#4D54E3", "#7433FF", "#3B6BD4",
    "#0066CC", "#3366B2", "#4159E0",
]

DEAD_CITY_WATCH_COLS = [
    "#000066"
]

CORRUPT_CITY_WATCH_COLS = [
    "#9999CC"
]

WANTED_COLS = [
    "#ff0033", "#cc3333", "#ff3300"
]

DEFAULT_REAL_NAME_BRIGHTNESS = 0.7

HEAD_HEADLINE_TEMPLATE = """
    <div xmlns="" class="event">
  [<a href="{URL}">{TIME}</a>]
   <span class="headline">{HEADLINE}</span><br/></div>"""

HEAD_DAY_TEMPLATE = """<h3 xmlns="">{DATE}</h3> {HEADLINES}"""

LIST_ITEM_TEMPLATE = """<li><a href="{URL}">{DISPLAY}</a></li>\n"""

FORMAT_SPECIFIER_REGEX = r"\[[P,D,L,N,V]([0-9]+)(?:_([0-9]+))?\]"

Chapter = NamedTuple("Chapter", (("title", str), ("nav_entry", NavbarEntry)))


def default_page_allocator(e: Event) -> Optional[Chapter]:
    # TODO: move hidden Event attribute into core
    if not e.pluginState.get("PageGeneratorPlugin", {}).get("hidden_event", False):
        week = date_to_weeks_and_days(get_game_start().date(), e.datetime.date()).week
        return Chapter(f"Week {week} News", NavbarEntry(f"news{week:02}.html", f"Week {week} Reports", week))


def event_url(e: Event, page: Optional[str] = None) -> str:
    """
    Generates the (relative) url pointing to this event's appearance on the news pages.
    """
    page = page or default_page_allocator(e).nav_entry.url
    return f"{page}#{e._Event__secret_id}"


class Manager(Protocol):
    """
    Interface for managers to process game state for correct player colouring.
    Implemented by CompetencyManager, DeathManager, WantedManager, and also TeamManager from MayWeekUtilitiesPlugin
    """
    def add_event(self, e: Event):
        """Interface for having a manager process an event."""


def default_color_fn(pseudonym: str,
                     assassin_model: Assassin,
                     e: Event,
                     plugin_managers: Sequence[Manager]) -> str:
    """
    Default rules for colouring pseudonyms.

    Determines competency, wantedness, and vitality at the event `e` from managers in `plugin_manager` that have been
    updated chronologically up to the event `e`.

    Colour is then assigned by `get_color` using this information.
    """
    is_city_watch = assassin_model.is_city_watch

    # retrieve info from managers
    is_wanted, dead, incompetent = False, False, False
    for manager in plugin_managers:
        if isinstance(manager, DeathManager):
            dead = manager.is_dead(assassin_model)
        elif isinstance(manager, CompetencyManager):
            incompetent = manager.is_inco_at(assassin_model, e.datetime)
        elif isinstance(manager, WantedManager):
            is_wanted = manager.is_player_wanted(assassin_model.identifier, time=e.datetime)

    return get_color(pseudonym, dead, incompetent, is_city_watch, is_wanted)


def get_color(pseudonym: str,
              dead: bool = False,
              incompetent: bool = False,
              is_city_watch: bool = False,
              is_wanted: bool = False) -> str:
    """Basic colouring rules that can be used by `ColorFn`s."""
    ind = sum(ord(c) for c in pseudonym)  # simple hash of the pseudonym
    # colour appropriately
    if is_wanted:
        if is_city_watch:
            return CORRUPT_CITY_WATCH_COLS[ind % len(CORRUPT_CITY_WATCH_COLS)]
        return WANTED_COLS[ind % len(WANTED_COLS)]
    if dead:
        if is_city_watch:
            return DEAD_CITY_WATCH_COLS[ind % len(DEAD_CITY_WATCH_COLS)]
        return DEAD_COLS[ind % len(DEAD_COLS)]
    if incompetent:
        return INCO_COLS[ind % len(INCO_COLS)]
    if pseudonym in HARDCODED_COLORS:
        return HARDCODED_COLORS[pseudonym]
    if is_city_watch:
        return CITY_WATCH_COLS[ind % len(CITY_WATCH_COLS)]
    return HEX_COLS[ind % len(HEX_COLS)]


def adjust_brightness(hexcode: str, factor: float) -> str:
    """
    Adjusts the brightness of the specified colour by the specified factor.
    Used for making real names slightly darker than pseudonyms.

    Args:
        hexcode (str): hexcode of the original colour, including an initial #
        factor (float): factor by which to multiply the brightness. If < 0 this will be set to 0.
            If the factor is such that any of the rgb values ends up > 255, they are capped at 255.

    Returns:
        str: the hexcode of the brightness-adjusted colour, (including an initial #).
    """
    rgb = (int(hexcode[i : i+2], 16) for i in (1, 3, 5))
    factor = max(factor, 0)
    scaled = (int(factor * x) for x in rgb)
    capped = (min(255, x) for x in scaled)
    return '#' + "".join(f"{x:02x}" for x in capped)


def get_real_name_brightness() -> float:
    """
    Gets the brightness factor to apply to colours when rendering players' real names.
    """
    return GENERIC_STATE_DATABASE.arb_state.get("REAL_NAME_BRIGHTNESS", DEFAULT_REAL_NAME_BRIGHTNESS)


def set_real_name_brightness(val: float):
    """
    Sets the brightness factor to apply to colours when rendering players' real names.
    Truncates negative values to 0.
    """
    GENERIC_STATE_DATABASE.arb_state["REAL_NAME_BRIGHTNESS"] = max(val, 0)



def escape_pseudonym_specifiers(string: str, assassin: Assassin) -> str:
    """
    Replaces the [] with {} in the pseudonym codes for a single assassin, to make them markdown-safe.
    """
    id_ = assassin._secret_id
    string = string.replace(f"[P{id_}]", f"{{P{id_}}}")
    for i in range(len(assassin.pseudonyms)):
        string = string.replace(f"[P{id_}_{i}]", f"{{P{id_}_{i}}}")
    string = string.replace(f"[D{id_}]", f"{{D{id_}}}")
    string = string.replace(f"[N{id_}]", f"{{N{id_}}}")
    string = string.replace(f"[L{id_}]", f"{{L{id_}}}")
    string = string.replace(f"[V{id_}]", f"{{V{id_}}}")
    return string


def substitute_pseudonyms(string: str, main_pseudonym: str, assassin: Assassin, color: str, dt: Optional[datetime.datetime] = None) -> str:
    """
    Renders [PX], [VX, [DX], [NX], [LX] [PX_i] pseudonym codes as HTML, for a single assassin

    Args:
        string (str): the string to render
        main_pseudonym (str): the pseudonym for [PX]
        assassin (Assassin): the assassin to render pseudonyym codes for
        color (str): hexcode (including #) of the colour to render the pseudonym in
        dt (datetime.datetime, optional): controls which pseudonyms will be rendered by [DX];
            only those set as valid from before this datetime will be rendered
            (needed for cases where players gain pseudonyms after dying)

    Returns:
        `string` with relevant pseudonym codes pertaining to `assassin` replaced by HTML renderings
    """
    dt = dt or get_now_dt()
    id_ = assassin._secret_id
    string = string.replace(f"{{P{id_}}}", PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(main_pseudonym)))
    for i in range(len(assassin.pseudonyms)):
        string = string.replace(f"{{P{id_}_{i}}}", PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(assassin.get_pseudonym(i))))
    string = string.replace(f"{{V{id_}}}", f"{{L{id_}}} ({{N{id_}}})")
    list_of_pseudonyms = " AKA ".join(PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(p)) for p in assassin.pseudonyms_until(dt))
    string = string.replace(f"{{L{id_}}}", list_of_pseudonyms)
    string = string.replace(f"{{D{id_}}}", list_of_pseudonyms)  # for backwards-compatibility; may remove in future
    string = string.replace(f"{{N{id_}}}",
        PSEUDONYM_TEMPLATE.format(
            COLOR=adjust_brightness(color, get_real_name_brightness()),
            PSEUDONYM=soft_escape(assassin.real_name)
        )
    )
    return string


headline_markdown_renderer = markdown.Markdown(extensions=['md_in_html'])


def inline_markdown(string: str) -> str:
    # To render markdown inline we need to wrap it in <td> tags and use the md_in_html extension.
    # Note that the `markdown='span'` attribute disappears after rendering, hence only 4 characters
    # need to be stripped from the start.
    # we also use a separate markdown renderer to not include the nl2br extension which renders newlines as <br />
    return headline_markdown_renderer.convert(f"<td markdown='span'>{string}</td>")[4:-5]


markdown_renderer = markdown.Markdown(extensions=['nl2br'])


def block_markdown(string: str) -> str:
    out = markdown_renderer.convert(string)
    if out.endswith("<br />"):
        out = out[:-6]
    return out


# required signature when replacing default_color_fn
ColorFn = Callable[[str, Assassin, Event, Sequence[Manager]], str]


def render_headline_and_reports(e: Event,
                                plugin_managers: Sequence[Manager] = tuple(),
                                color_fn: ColorFn = default_color_fn) -> (str, Dict[Tuple[str, int], str]):
    """
    Produces the HTML renderings of an events headline and its reports

    Args:
        e (Event): the event to render the headline and reports of
        plugin_managers (Sequence[Manager]): A sequence of managers that have been updated up to the event
            `e`. When called by PageGeneratorPlugin this will contain a CompetencyManager, DeathManager, and
            WantedManager, but other plugins may use it differently.
        color_fn (ColorFn): A function taking a pseudonym, assassin model, event model and a sequence of Managers, and
            returning a colour hexcode (including #). Defaults to `default_color_fn`.

    Returns:
        (str, Dict[Tuple[str, int], str]): A tuple of:
            - the event `e`'s headline rendered as HTML
            - a dict mapping tuples (assasin identifier, pseudonym index) to rendered HTML report bodies
    """
    plugin_managers = plugin_managers or tuple()

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

            color = color_fn(
                pseudonym,
                assassin_model,
                e,
                plugin_managers
            )

            candidate_pseudonyms.append((assassin_model, pseudonym, color))

    # first, convert from [] pseudonym specifies to {} pseudonym specifiers to make them markdown-safe
    for (assassin_model, _, _) in candidate_pseudonyms:
        headline = escape_pseudonym_specifiers(headline, assassin_model)
        for (k, r) in reports.items():
            reports[k] = escape_pseudonym_specifiers(r, assassin_model)

    # next, render markdown.
    headline = inline_markdown(headline)
    for (k, r) in reports.items():
        # only render markdown for non-html reports. it's perfectly safe to render markdown in html reports, but the
        # spacing works differently to html, so they won't come out as players expect
        if not r.startswith(HTML_REPORT_PREFIX):
            reports[k] = block_markdown(r)

    # finally, substitute pseudonyms. We need to do this *after* rendering markdown so that they don't accidentally
    # introduce unwanted markdown formatting.
    for (assassin_model, pseudonym, color) in candidate_pseudonyms:
        headline = substitute_pseudonyms(headline, pseudonym, assassin_model, color, e.datetime)
        for (k, r) in reports.items():
            reports[k] = substitute_pseudonyms(r, pseudonym, assassin_model, color, e.datetime)

    return headline, reports


def render_event(e: Event,
                 page: str,
                 plugin_managers: Sequence[Manager] = tuple(),
                 color_fn: ColorFn = default_color_fn) -> (str, str):
    """
    Renders the full HTML for the event, including headline and reports
    Also gives the HTML rendering of the headline for the headlines page.

    Args:
        e (Event): the event to render as html
        page (str): the page that the Event is being rendered for. Needed for the correct href in the headline.
        plugin_managers (Sequence[Manager]): A sequence of managers that have been updated up to the event
            `e`. When called by PageGeneratorPlugin this will contain a CompetencyManager, DeathManager, and
            WantedManager, but other plugins may use it differently.
        color_fn (ColorFn): A function taking a pseudonym, assassin model, event model and a sequence of Managers, and
            returning a colour hexcode (including #). Defaults to `default_color_fn`.

    Returns:
        (str, str): A tuple of (event_html, headline_html), i.e. html renderings of, respectively, the whole event
        (headline and reports, for news pages), and the headline only (for the headlines page).
    """
    plugin_managers = plugin_managers or tuple()
    headline, reports = render_headline_and_reports(
        e,
        plugin_managers=plugin_managers,
        color_fn=color_fn
    )
    report_list = []
    for ((assassin, pseudonym_index), r) in reports.items():
        # Umpires must tell AU to NOT escape HTML
        # If they tell it not to, they do so at their own risk. Make sure you know what you want to do!
        # TODO: Initialize the default report template with some helpful HTML tips, such as this fact
        assassin_model = ASSASSINS_DATABASE.get(assassin)
        if pseudonym_index is None:
            # Auto pseudonym mode
            # unfortunately can't do `= pseudonym_index or` because pseudonym_index can also be 0....
            pseudonym_index = e.assassins[assassin]
        pseudonym = assassin_model.get_pseudonym(pseudonym_index)
        color = color_fn(
            pseudonym,
            assassin_model,
            e,
            plugin_managers
        )

        painted_pseudonym = PSEUDONYM_TEMPLATE.format(COLOR=color, PSEUDONYM=soft_escape(pseudonym))

        report_list.append(
            REPORT_TEMPLATE.format(PSEUDONYM=painted_pseudonym, REPORT_COLOR=color, REPORT=r)
        )

    report_text = "".join(report_list)
    time_str = datetime_to_time_str(e.datetime)
    event_html = EVENT_TEMPLATE.format(
        ID=e._Event__secret_id,
        TIME=time_str,
        HEADLINE=headline,
        REPORTS=report_text
    )
    headline_html = HEAD_HEADLINE_TEMPLATE.format(
        URL=event_url(e, page),
        TIME=time_str,
        HEADLINE=headline
    )
    return event_html, headline_html

# required signature when replacing default_page_allocator
PageAllocator = Callable[[Event], Optional[Chapter]]

def render_all_events(page_allocator: PageAllocator = default_page_allocator,
                      color_fn: ColorFn = default_color_fn,
                      plugin_managers: Sequence[Manager] = tuple()) -> (List[str], Dict[Chapter, List[str]]):
    """
    Produces renderings of all events, sorted into pages according to `page_allocator`.

    Args:
        page_allocator (PageAllocator): A function mapping an Event to a `Chapter` namedtuple giving the title and
            navbar entry of the page the event is to be rendered on, or `None` if the event should be skipped.
            E.g. an event in week 2 would be mapped to
            Chapter("Week 2 News", NavbarEntry("week02.html", "Week 2 Reports", 2)).
        color_fn (ColorFn): A function taking a pseudonym, assassin model, event model and a sequence of Managers, and
            returning a colour hexcode (including #). Defaults to `default_color_fn`.
        plugin_managers (Sequence[Manager]): Sequence of additional, newly-initialised Managers that will be
            passed into `color_fn` along with a CompetencyManager, DeathManager, and WantedManager.

            Defaults to an empty tuple in which case only the managers just named will be used.

            Events are added to these managers in chronological order.

    Returns:
        A tuple of: a list of strings where each element is the HTML rendering of one day's headlines, and a dict
            mapping tuples (page path, page title) to a list of strings where each element is the HTML rendering of one day's reports.
    """
    events = list(EVENTS_DATABASE.events.values())
    events.sort(key=lambda event: event.datetime)
    start_datetime = get_game_start()

    # maps chapter (news week) to day-of-week to list of reports
    # this is 1-indexed (week 1 is first week of game)
    # days are 0-indexed (fun, huh?)
    events_for_chapter = {}
    headlines_for_day = {}
    competency_manager = CompetencyManager(start_datetime)
    death_manager = DeathManager()
    wanted_manager = WantedManager()
    plugin_managers = (competency_manager, death_manager, wanted_manager, *(plugin_managers or tuple()))

    for e in events:
        # don't skip adding hidden events to managers, in case a player dies in a hidden event, etc.
        for manager in plugin_managers:
            manager.add_event(e)

        chapter = page_allocator(e)
        if not chapter:
            continue

        event_text, headline_text = render_event(
            e,
            chapter.nav_entry.url,
            color_fn=color_fn,
            plugin_managers=plugin_managers,
        )

        events_for_chapter.setdefault(chapter, {}).setdefault(e.datetime.date(), []).append(event_text)
        headlines_for_day.setdefault(e.datetime.date(), []).append(headline_text)

    chapters = {}
    for (w, d_dict) in events_for_chapter.items():
        outs = []
        for (d, events_list) in sorted(d_dict.items()):
            all_event_text = "".join(events_list)
            day_text = DAY_TEMPLATE.format(
                DATE=d.strftime("%A, %d %B"),
                EVENTS=all_event_text
            )
            outs.append(day_text)
        chapters[w] = outs

    head_days = []
    for (d, headlines_list) in sorted(headlines_for_day.items()):
        head_days.append(
            HEAD_DAY_TEMPLATE.format(
                DATE=d.strftime("%A, %d %B"),
                HEADLINES="".join(headlines_list)
            )
        )

    return head_days, chapters


def generate_navbar(navbar_entries: List[NavbarEntry], filename: str):
    """
    Generates a html list of page links, for inclusion into header.html using `w3-include-html`.

    Args:
        navbar_entries (list(NavbarEntry)): each NavberEntry namedtuple specifies a url, display text, and position.
            The position is a float value and the entries are rendered from top to bottom in *ascending* order of
            position.
        filename (str): the filename to save the list under (in the WEBPAGE_WRITE_LOCATION directory).
    """
    with open(WEBPAGE_WRITE_LOCATION / filename, "w+", encoding="utf-8", errors="ignore") as f:
        f.write("\n".join(
            LIST_ITEM_TEMPLATE.format(
                URL=entry.url,
                DISPLAY=entry.display
            ) for entry in sorted(navbar_entries, key=lambda e: e.position)
        ))


def generate_news_pages(headlines_path: str,
                        page_allocator: PageAllocator = default_page_allocator,
                        color_fn: ColorFn = default_color_fn,
                        plugin_managers: Sequence[Manager] = tuple(),
                        news_list_path: str = ""):
    """
    Generates news pages sorted according to `page_allocator`.

    Args:
        headlines_path (str): filename to save the headlines page under. If empty ("") no headlines page is generated.
        page_allocator (PageAllocator): A function mapping an Event to a `Chapter` namedtuple giving the name and title
            of the page the event is to be rendered on, or `None` if the event should be skipped.
            E.g. an event in week 2 would be mapped to Chapter("week02", "Week 2 News").
        color_fn (ColorFn): A function taking a pseudonym, assassin model, event model and a sequence of Managers, and
            returning a colour hexcode (including #). Defaults to `default_color_fn`.
        plugin_managers (Sequence[Manager]): Sequence of additional, newly-initialised Managers that will be
            passed into `color_fn` along with a CompetencyManager, DeathManager, and WantedManager.

            Defaults to an empty tuple in which case only the managers just named will be used.

            Events are added to these managers in chronological order.
        news_list_path (str): filename to save the list of news pages for the header under. If empty ("") no list is
            generated.
    """
    headline_days, chapters = render_all_events(
        page_allocator=page_allocator,
        color_fn=color_fn,
        plugin_managers=plugin_managers
    )

    news_navbar_entries = []

    # generate headlines page
    if headlines_path and headline_days:
        head_page_text = HEAD_TEMPLATE.format(
            CONTENT="".join(headline_days),
            YEAR=str(get_now_dt().year)
        )
        with open(WEBPAGE_WRITE_LOCATION / headlines_path, "w+", encoding="utf-8", errors="ignore") as F:
            F.write(head_page_text)
        news_navbar_entries.append(NavbarEntry(headlines_path, "Headlines", -1))

    # generate news pages
    for chapter, days in chapters.items():
        week_page_text = NEWS_TEMPLATE.format(
            TITLE=chapter.title,
            DAYS="".join(days),
            YEAR=str(get_now_dt().year)
        )
        with open(WEBPAGE_WRITE_LOCATION / chapter.nav_entry.url, "w+", encoding="utf-8", errors="ignore") as F:
            F.write(week_page_text)
        news_navbar_entries.append(chapter.nav_entry)

    generate_navbar(news_navbar_entries or [NavbarEntry("#", "None Yet", 0)], news_list_path)
