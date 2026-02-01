import os
import pathlib
import datetime
from typing import List, Optional, Tuple, Any, Dict, Iterable

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.model.Event import Event
from AU2.html_components.HTMLComponent import HTMLComponent
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.OptionalDatetimeEntry import OptionalDatetimeEntry
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.FloatEntry import FloatEntry
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export, ConfigExport
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.render_utils import get_color, render_headline_and_reports, event_url
from AU2.plugins.util.ScoreManager import ScoreManager
from AU2.plugins.util.CompetencyManager import CompetencyManager
from AU2.plugins.util.WantedManager import WantedManager
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.date_utils import get_now_dt, timestamp_to_dt, dt_to_timestamp, DATETIME_FORMAT
from AU2.plugins.util.game import get_game_start, get_game_end

OPENSEASON_TABLE_TEMPLATE = """
<table xmlns="" class="playerlist">
  <tr><th>Real Name</th><th>Address</th><th>College</th><th>Room Water Weapons Status</th><th>Notes</th><th>Points</th></tr>
  {ROWS}
</table>
"""

OPENSEASON_ROW_TEMPLATE = """
<tr><td>{NAME}</td><td>{ADDRESS}</td><td>{COLLEGE}</td><td>{WATER_STATUS}</td><td>{NOTES}</td><td>{POINTS:g}</tr>
"""

OPENSEASON_PAGE_TEMPLATE: str
OPENSEASON_PAGE_TEMPLATE_PATH: pathlib.Path = ROOT_DIR / "plugins" / "custom_plugins" / "html_templates" / "openseason.html"
with open(OPENSEASON_PAGE_TEMPLATE_PATH, "r", encoding="utf-8", errors="ignore") as F:
    OPENSEASON_PAGE_TEMPLATE = F.read()

# LHS is table header, RHS is template string for table cell values
# note the order here determines the order in which columns are displayed
STATS_COLUMN_TEMPLATES = {
    "Position": "{RANK}",
    "Died at": "{DEATHS}",
    "Real Name": "{NAME}",
    "Pseudonym": "{PSEUDONYMS}",
    "Number of Attempts": "{ATTEMPTS}",
    "Number of Kills": "{KILLS}",
    "Conkers Score": "{CONKERS}",
    "Score": "{SCORE}"
}


def stats_row_template(columns: Iterable[str]) -> str:
    """Generate a row template for the stats page from the given columns"""
    return "<tr>" + "".join(f"<td>{STATS_COLUMN_TEMPLATES[col]}</td>" for col in columns) + "</tr>"


def stats_table_template(columns: Iterable[str]) -> str:
    """Generate a table template for the stats page from the given columns"""
    return (
            '<table xmlns="" class="playerlist"><tr>'
            + ''.join(f'<th>{header}</th>' for header in columns)
            + '</tr> {ROWS} </table>'
    )


STATS_ORDERING_KEYS = {
    "By Death (AU1 style)": lambda score_manager, a: (-score_manager.get_rating(a), -score_manager.get_score(a)),
    "By Kills (London style)": lambda score_manager, a: (-score_manager.get_kills(a), -score_manager.get_conkers(a)),
}

STATS_PAGE_TEMPLATE: str
STATS_PAGE_TEMPLATE_PATH: pathlib.Path = ROOT_DIR / "plugins" / "custom_plugins" / "html_templates" / "stats.html"
with open(STATS_PAGE_TEMPLATE_PATH, "r", encoding="utf-8", errors="ignore") as F:
    STATS_PAGE_TEMPLATE = F.read()

KILLTREE_PATH = "killtree.html"
KILLTREE_EMBED = """
<h2>Kill tree</h2>
<script type="text/javascript">
  function iframeLoaded() {
      var iFrameID = document.getElementById('idIframe');
      if(iFrameID) {
            iFrameID.height = iFrameID.contentWindow.document.body.scrollHeight + "px";
      }   
  }
</script>   
""" + f"""
<iframe src="{KILLTREE_PATH}" width="100%" style="border: none; aspect-ratio: 4 / 3" scrolling="no" id="idIframe" onload="iframeLoaded()"></iframe>
"""
KILLTREE_LINK = f"""
<p>View a visualisation of the kill graph <a href={KILLTREE_PATH}>here</a>.</p>
"""

NODE_SHAPE = "dot"
def generate_killtree_visualiser(events: List[Event], score_manager: ScoreManager) -> str:
    # local import because importing pyvis every time impacts performance significantly
    try:
        from pyvis.network import Network
        import lxml.html
    except ModuleNotFoundError:
        return "Skipping killtree visualisation due to missing modules -- check `requirements.txt`."

    # track competency and wantedness for edge colouring
    competency_manager = CompetencyManager(get_game_start())
    wanted_manager = WantedManager()

    net = Network(directed=True, cdn_resources="in_line", height="calc(100vh - 90px)", select_menu=True)
    added_nodes = set()
    for e in events:
        # construct kill tree network
        for (killer, victim) in e.kills:
            competency_manager.add_event(e)
            wanted_manager.add_event(e)
            killer_model = ASSASSINS_DATABASE.get(killer)
            victim_model = ASSASSINS_DATABASE.get(victim)
            killer_searchable = f"{killer_model.all_pseudonyms(fn=lambda x: x)} ({killer_model.real_name})"
            victim_searchable = f"{victim_model.all_pseudonyms(fn=lambda x: x)} ({victim_model.real_name})"
            if killer not in added_nodes:
                net.add_node(
                    killer_searchable,
                    label=killer_model.real_name + (" (City Watch)" if killer_model.is_city_watch else ""),
                    shape=NODE_SHAPE,
                    color=get_color(killer_model.get_pseudonym(0), is_city_watch=killer_model.is_city_watch),
                    title=killer_searchable,
                    value=1 + score_manager.get_conkers(killer_model)
                )
                added_nodes.add(killer)
            if victim not in added_nodes:
                net.add_node(
                    victim_searchable,
                    label=victim_model.real_name + (" (City Watch)" if victim_model.is_city_watch else ""),
                    shape=NODE_SHAPE,
                    color=get_color(victim_model.get_pseudonym(0), is_city_watch=victim_model.is_city_watch),
                    title=victim_searchable,
                    value=1 + score_manager.get_conkers(victim_model)
                )
                added_nodes.add(victim)
            headline, _ = render_headline_and_reports(e, plugin_managers=(competency_manager, wanted_manager))
            plaintext_headline = lxml.html.fromstring(f"<html>{headline}</html>").text_content()
            net.add_edge(killer_searchable, victim_searchable,
                         label=e.datetime.strftime(DATETIME_FORMAT),
                         color=get_color(
                             victim_model.get_pseudonym(e.assassins.get(victim, 0)),
                             is_city_watch=victim_model.is_city_watch,
                             incompetent=competency_manager.is_inco_at(victim_model, e.datetime),
                             is_wanted=wanted_manager.is_player_wanted(victim, e.datetime)
                         ),
                         title=f"[{e.datetime.strftime(DATETIME_FORMAT)}] {plaintext_headline}"
                         )
    with open(os.path.join(WEBPAGE_WRITE_LOCATION, KILLTREE_PATH), "w+", encoding="utf-8") as F:
        F.write(net.generate_html())
    return "" # empty string indicates success


@registered_plugin
class ScoringPlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("ScoringPlugin")

        self.html_ids = {
            "Start": self.identifier + "_openseason_start",
            "Formula": self.identifier + "_formula",
            "Bonus": self.identifier + "_bonus",
            "Assassin": self.identifier + "_assassin",
            "Stats Columns": self.identifier + "_stats_cols",
            "Visualise Kills?": self.identifier + "_visualise_kills",
            "Stats Order": self.identifier + "_stats_order",
            "Generate Stats Page?": self.identifier + "_stats_page"
        }

        self.plugin_state = {
            "Start": {'id': self.identifier + "_openseason_start", 'default': None},
            "Formula": {'id': self.identifier + "_score_formula", 'default': ''},
            "Stats Columns": {'id': self.identifier + "_stats_cols", 'default': [
                "Real Name", "Pseudonym", "Number of Kills", "Conkers Score"
            ]},
            "Visualise Kills?": {'id': self.identifier + "_visualise_kills", 'default': True},
            "Stats Order": {'id': self.identifier + "_stats_order", 'default': 'By Kills (London style)'}
        }

        self.assassin_plugin_state = {
            "Bonus": {'id': self.identifier + "_bonus", 'default': 0}
        }

        self.exports = [
            Export(
                "scoring_set_bonuses",
                "Scoring -> Set bonuses",
                self.ask_set_bonuses,
                self.answer_set_bonuses,
                (self.gather_assassins_and_bonuses,)
            ),
        ]

        self.config_exports = [
            ConfigExport(
                "scoring_start_open_season",
                "Scoring -> Set Open Season start",
                self.ask_start_open_season,
                self.answer_start_open_season
            ),
            ConfigExport(
                "scoring_set_formula",
                "Scoring -> Set formula",
                self.ask_set_formula,
                self.answer_set_formula
            )
        ]

    # plugin state management is copied from CityWatchPlugin
    def gsdb_get(self, plugin_state_id: str):
        return GENERIC_STATE_DATABASE.arb_state.get(self.identifier, {}).get(self.plugin_state[plugin_state_id]['id'],
                                                                             self.plugin_state[plugin_state_id][
                                                                                 'default'])

    def gsdb_set(self, plugin_state_id: str, data: Any):
        GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {})[
            self.plugin_state[plugin_state_id]['id']] = data

    def gsdb_remove(self, plugin_state_id: str):
        """Removes a plugin state key from the gsdb, i.e. reverts to default"""
        GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {}).pop(self.plugin_state[plugin_state_id]['id'],
                                                                             None)

    # does similar to above but for Assassin.plugin_state
    def aps_get(self, assassin_id: str, plugin_state_id: str) -> Any:
        assassin = ASSASSINS_DATABASE.get(assassin_id)
        return assassin.plugin_state.get(self.identifier, {}).get(self.assassin_plugin_state[plugin_state_id]['id'],
                                                                  self.assassin_plugin_state[plugin_state_id][
                                                                      'default'])

    def aps_set(self, assassin_id: str, plugin_state_id: str, data: Any):
        assassin = ASSASSINS_DATABASE.get(assassin_id)
        assassin.plugin_state.setdefault(self.identifier, {})[self.assassin_plugin_state[plugin_state_id]['id']] = data

    def gather_assassins_and_bonuses(self) -> List[Tuple[str, str]]:
        """Lists assassins with their bonuses"""
        return [(f"{ident} -- {self.aps_get(ident, 'Bonus')}", ident)
                for ident in ASSASSINS_DATABASE.get_identifiers()]

    def ask_set_bonuses(self, ident: str) -> List[HTMLComponent]:
        current_bonus = self.aps_get(ident, "Bonus")
        components = [
            HiddenTextbox(
                identifier=self.html_ids["Assassin"],
                default=ident
            ),
            FloatEntry(
                identifier=self.html_ids["Bonus"],
                title="Bonus points",
                default=current_bonus
            )
        ]
        return components

    def answer_set_bonuses(self, html_response: Dict[str, Any]) -> List[HTMLComponent]:
        new_bonus = html_response[self.html_ids["Bonus"]]
        ident = html_response[self.html_ids["Assassin"]]
        self.aps_set(ident, "Bonus", new_bonus)
        return [Label("[SCORING] Set bonus.")]

    def _generate_stats_page(self,
                             columns: List[str],
                             generate_killtree: bool,
                             stats_order: str) -> List[HTMLComponent]:
        components = []
        openseason_end = get_game_end()
        # use a score manager to count kills, conkers, and attempts
        # don't need to set the formula because we aren't going to fetch scores
        full_players = ASSASSINS_DATABASE.get_filtered(include=lambda a: not a.is_city_watch,
                                                       include_hidden=lambda a: not a.is_city_watch)
        formula = self.gsdb_get("Formula")
        score_manager = ScoreManager({a.identifier for a in full_players}, formula=formula, game_end=openseason_end)
        events = sorted(EVENTS_DATABASE.events.values(), key=lambda e: e.datetime)
        for e in events:
            score_manager.add_event(e)
        rows = []

        full_players.sort(key=lambda a: STATS_ORDERING_KEYS[stats_order](score_manager, a))
        for rank, p in enumerate(full_players):
            # list of datetimes at which the player died, if applicable,
            # each with a link to the corresponding event on the news pages
            deaths = [f'<a href="{event_url(e)}">{e.datetime.strftime(DATETIME_FORMAT)}</a>'
                      if openseason_end is None or e.datetime < openseason_end
                      else "Duel"
                      for e in score_manager.get_death_events(p)]
            rows.append(stats_row_template(columns).format(
                NAME=p.real_name,
                PSEUDONYMS=p.all_pseudonyms(),
                KILLS=score_manager.get_kills(p),
                CONKERS=score_manager.get_conkers(p),
                ATTEMPTS=score_manager.get_attempts(p),
                DEATHS='<br />'.join(deaths) if deaths else "&mdash;",
                # RANK is simply the position that a player appears according to whichever metric we are using,
                # e.g. "kills" or "rating".
                # But if players are tied according to this ordering metric, we want to make that clear.
                # We do this by replacing a player's rank with a " -- representing a "ditto" sign -- if they are listed
                # below a player they are tied with.
                RANK=(rank+1
                      if rank == 0 or
                      STATS_ORDERING_KEYS[stats_order](score_manager, full_players[rank-1])
                        != STATS_ORDERING_KEYS[stats_order](score_manager, p)
                      else '"'),
                SCORE=score_manager.get_score(p)
            ))
        table_str = stats_table_template(columns).format(ROWS="".join(rows))

        # kill tree visualiser
        killtree_embed = ""
        killtree_link = ""
        if generate_killtree:
            msg = generate_killtree_visualiser(events, score_manager)
            if msg:
                components.append(Label(f"[WARNING] [SCORING] {msg}"))
            else:
                killtree_link = KILLTREE_LINK
                killtree_embed = KILLTREE_EMBED
                components.append(Label("[SCORING] Generated killtree page."))

        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "stats.html"), "w+", encoding="utf-8") as F:
            F.write(
                STATS_PAGE_TEMPLATE.format(
                    YEAR=get_now_dt().year,
                    TABLE=table_str,
                    KILLTREE_EMBED=killtree_embed,
                    KILLTREE_LINK=killtree_link
                )
            )

        components.append(Label("[SCORING] Generated stats page."))
        return components

    def ask_start_open_season(self):
        ts = self.gsdb_get("Start")
        return [
            OptionalDatetimeEntry(identifier=self.html_ids["Start"],
                          title="Enter when Open Season should start (blank for \"never\")",
                          default=timestamp_to_dt(ts) if ts else get_now_dt())
        ]

    def answer_start_open_season(self, html_response):
        start = html_response[self.html_ids["Start"]]
        if start:
            self.gsdb_set("Start", dt_to_timestamp(start))
        else:
            self.gsdb_remove("Start")
        return [Label("[SCORING] Set open season start.")]

    def ask_set_formula(self):
        # TODO: have a Formula component that validates the formula,
        #       and give detail on formula syntax
        return [
            Label("""Scoring formula instructions:
Parameters:
    a: attempts
    b: bonus points -- awarded manually using Scoring -> Set bonuses
    k: kills -- excludes kills of the city watch, and of players who had already died when the kill was made
    c: conkers -- a player's conkers score is the number of kills made by the player, plus the sum of \
the conkers of all players killed by the player, ignoring any kills that do not count towards the kill score \
as defined above

Syntax:
    Currently the scoring formula is passed directly to the Python eval() function.
    This means the syntax is that of a Python expression.
    For reference, the arithmetic symbols are
        + addition
        - subtraction
        * multiplication
        / division
        ** exponentiation
    If you want to be fancy, `import math` is run right before the formula is evaluated,
    so you can use functions from this module too.
"""),
            DefaultNamedSmallTextbox(identifier=self.html_ids["Formula"],
                                     title="Scoring formula",
                                     default=self.gsdb_get("Formula"))
        ]

    def answer_set_formula(self, html_response):
        self.gsdb_set("Formula", html_response[self.html_ids["Formula"]])
        return [Label("[SCORING] Set scoring formula.")]

    def formula_is_valid(self, formula: Optional[str] = None) -> bool:
        """
        Checks whether the scoring formula is valid.

        Parameters:
            formula: the scoring formula in string form. Defaults to the value from the plugin.

        Returns:
            True if formula is valid, False otherwise
        """
        if formula is None:
            formula = self.gsdb_get("Formula")
        # since we don't have the formula parser yet,
        # we crudely use a try-except evaluating the expression
        a = 0
        b = 0
        c = 0
        k = 0
        import math
        try:
            eval(formula)
            return True
        except Exception:
            return False

    def _generate_openseason_page(self):
        # don't generate open season page if open season hasn't started!
        open_season_start = timestamp_to_dt(self.gsdb_get("Start"))
        if not open_season_start or open_season_start > get_now_dt():
            return []
        # also don't generate if formula is invalid
        formula = self.gsdb_get("Formula")
        if not self.formula_is_valid(formula):
            return [Label("[WARNING] [SCORING] Invalid scoring formula -- skipping openseason page!")]

        # need to include hidden assassins so that resurrecting as part of the city watch doesn't stop kills counting
        score_manager = ScoreManager(ASSASSINS_DATABASE.get_identifiers(include=lambda a: not a.is_city_watch,
                                                                        include_hidden=True),
                                     formula=formula,
                                     bonuses={
                                         ident: self.aps_get(ident, "Bonus")
                                         for ident in ASSASSINS_DATABASE.get_identifiers(include_hidden=True)
                                     })
        events = sorted(EVENTS_DATABASE.events.values(),
                        key=lambda e: e.datetime)
        openseason_end = get_game_end() or get_now_dt()
        for e in events:
            # stops the duel changing the openseason page
            if e.datetime > openseason_end:
                break
            score_manager.add_event(e)

        table_str = "Something went wrong..."
        if score_manager.live_assassins:
            # score_manager caches score, so calling twice is fine!
            # *negative* of score is used for sorting so that high scorers end up at the top of the page
            live_assassins = sorted((ASSASSINS_DATABASE.get(ident) for ident in score_manager.live_assassins
                                     if not ASSASSINS_DATABASE.get(ident).hidden),
                                    key=lambda a: (-score_manager.get_score(a), a.college.lower(), a.real_name.lower()))
            rows = []
            for a in live_assassins:
                rows.append(
                    OPENSEASON_ROW_TEMPLATE.format(
                        NAME=a.real_name,
                        ADDRESS=a.address,
                        COLLEGE=a.college,
                        WATER_STATUS=a.water_status,
                        NOTES=a.notes,
                        POINTS=score_manager.get_score(a)
                    )
                )
            table_str = OPENSEASON_TABLE_TEMPLATE.format(ROWS="".join(rows))

        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "openseason.html"), "w+", encoding="utf-8") as F:
            F.write(
                OPENSEASON_PAGE_TEMPLATE.format(
                    YEAR=get_now_dt().year,
                    TABLE=table_str
                )
            )

        return [Label("[SCORING] Generated openseason page.")]

    def _should_generate_stats_page(self) -> bool:
        game_end = get_game_end()
        return (game_end < get_now_dt()) if game_end else False

    def on_page_request_generate(self) -> List[HTMLComponent]:
        components = []
        # stats page generation
        if self._should_generate_stats_page():
            selected_cols: List[str] = self.gsdb_get("Stats Columns")
            all_cols = list(STATS_COLUMN_TEMPLATES.keys())
            generate_killtree: bool = self.gsdb_get("Visualise Kills?")
            components.extend([
                SelectorList(identifier=self.html_ids["Stats Columns"],
                                           title="Which columns should be included in the player stats table?",
                                           options=all_cols,
                                           defaults=selected_cols),
                InputWithDropDown(identifier=self.html_ids["Stats Order"],
                                                title="How should players be ordered on the stats page?",
                                                options=list(STATS_ORDERING_KEYS.keys()),
                                                selected=self.gsdb_get("Stats Order")),
                Checkbox(identifier=self.html_ids["Visualise Kills?"],
                                       title="Generate visualisation of kill graph?",
                                       checked=generate_killtree),
                HiddenTextbox(identifier=self.html_ids["Generate Stats Page?"], default="True")
            ])
        return components

    def on_page_generate(self, htmlResponse) -> List[HTMLComponent]:
        components = []
        components.extend(self._generate_openseason_page())
        if htmlResponse.get(self.html_ids["Generate Stats Page?"], "False") == "True":
            # this is silly but needed to fix a bug where columns end up in the wrong order
            columns: List[str] = [c for c in STATS_COLUMN_TEMPLATES if
                                  c in htmlResponse[self.html_ids["Stats Columns"]]]
            self.gsdb_set("Stats Columns", columns)
            generate_killtree: bool = htmlResponse[self.html_ids["Visualise Kills?"]]
            self.gsdb_set("Visualise Kills?", generate_killtree)
            stats_order = htmlResponse[self.html_ids["Stats Order"]]
            self.gsdb_set("Stats Order", stats_order)
            components.extend(self._generate_stats_page(columns, generate_killtree, stats_order))

        return components
