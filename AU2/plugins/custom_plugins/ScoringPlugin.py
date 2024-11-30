import os
from typing import List, Optional, Tuple, Any, Dict

from AU2 import ROOT_DIR
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.html_components.HTMLComponent import HTMLComponent
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.OptionalDatetimeEntry import OptionalDatetimeEntry
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.FloatEntry import FloatEntry
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export, ConfigExport
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.custom_plugins.PageGeneratorPlugin import get_color
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.ScoreManager import ScoreManager
from AU2.plugins.util.CompetencyManager import CompetencyManager
from AU2.plugins.util.WantedManager import WantedManager
from AU2.plugins.util.date_utils import get_now_dt, timestamp_to_dt, dt_to_timestamp
from AU2.plugins.util.game import get_game_start

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
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "openseason.html"), "r", encoding="utf-8",
          errors="ignore") as F:
    OPENSEASON_PAGE_TEMPLATE = F.read()

STATS_TABLE_TEMPLATE = """
<table xmlns="" class="playerlist">
<tr><th>Real Name</th><th>Pseudonym</th><th>Number of Attempts</th><th>Number of Kills</th><th>Conkers Score</th></tr>
  {ROWS}
</table>
"""

STATS_ROW_TEMPLATE = """
<tr><td>{NAME}</td><td>{PSEUDONYMS}</td><td>{ATTEMPTS}</td><td>{KILLS}</td><td>{CONKERS}</td></tr>
"""

STATS_PAGE_TEMPLATE: str
with open(os.path.join(ROOT_DIR, "plugins", "custom_plugins", "html_templates", "stats.html"), "r", encoding="utf-8",
          errors="ignore") as F:
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

DATETIME_FORMAT = "%Y-%m-%d %H:%M"

@registered_plugin
class ScoringPlugin(AbstractPlugin):
    def __init__(self):
        super().__init__("ScoringPlugin")

        self.html_ids = {
            "Start": self.identifier + "_openseason_start",
            "Formula": self.identifier + "_formula",
            "Bonus": self.identifier + "_bonus",
            "Assassin": self.identifier + "_assassin"
        }

        self.plugin_state = {
            "Start": {'id': self.identifier + "_openseason_start", 'default': None},
            "Formula": {'id': self.identifier + "_score_formula", 'default': ''}
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
            Export(
                "scoring_stats_page",
                "Scoring -> Generate stats page",
                self.ask_stats_page,
                self.answer_stats_page,
            )
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
            ),
        ]

    # plugin state management is copied from PolicePlugin
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

    def ask_stats_page(self) -> List[HTMLComponent]:
        return []

    def answer_stats_page(self, htmlResponse) -> List[HTMLComponent]:
        components = []
        # use a score manager to count kills, conkers, and attempts
        # don't need to set the formula because we aren't going to fetch scores
        full_players = ASSASSINS_DATABASE.get_filtered(include=lambda a: not a.is_police,
                                                          include_hidden=lambda a: not a.is_police)
        score_manager = ScoreManager({a.identifier for a in full_players})
        events = sorted(EVENTS_DATABASE.events.values(),
                        key=lambda e: e.datetime)
        for e in events:
            score_manager.add_event(e)

        rows = []
        # the existing stats pages order by kills so do that here too
        for p in sorted(full_players, key=lambda a: score_manager.get_kills(a), reverse=True):
            rows.append(STATS_ROW_TEMPLATE.format(
                NAME=p.real_name,
                PSEUDONYMS=p.all_pseudonyms(),
                KILLS=score_manager.get_kills(p),
                CONKERS=score_manager.get_conkers(p),
                ATTEMPTS=score_manager.get_attempts(p)
            ))
        table_str = STATS_TABLE_TEMPLATE.format(ROWS="".join(rows))

        # kill tree visualiser
        # skip if we don't have pyvis installed
        try:
            #raise NotImplementedError() # skip for now
            from pyvis.network import Network

            # track competency and wantedness for edge colouring
            competency_manager = CompetencyManager(get_game_start())
            wanted_manager = WantedManager()

            net = Network(directed=True, cdn_resources="in_line", height="calc(100vh - 90px)", select_menu=True)
            NODE_SHAPE = "dot"
            added_nodes = set()
            for e in events:
                # construct kill tree network
                for (killer, victim) in e.kills:
                    competency_manager.add_event(e)
                    wanted_manager.add_event(e)
                    killer_model = ASSASSINS_DATABASE.get(killer)
                    victim_model = ASSASSINS_DATABASE.get(victim)
                    killer_searchable = f"{killer_model.all_pseudonyms()} ({killer_model.real_name})"
                    victim_searchable = f"{victim_model.all_pseudonyms()} ({victim_model.real_name})"
                    if killer not in added_nodes:
                        net.add_node(
                            killer_searchable,
                            label=killer_model.real_name + (" (Police)" if killer_model.is_police else ""),
                            shape=NODE_SHAPE,
                            color=get_color(killer_model.get_pseudonym(0), is_police=killer_model.is_police),
                            title=killer_searchable,
                            value=1+score_manager.get_conkers(killer_model)
                        )
                        added_nodes.add(killer)
                    if victim not in added_nodes:
                        net.add_node(
                            victim_searchable,
                            label=victim_model.real_name + (" (Police)" if victim_model.is_police else ""),
                            shape=NODE_SHAPE,
                            color=get_color(victim_model.get_pseudonym(0), is_police=victim_model.is_police),
                            title=victim_searchable,
                            value=1+score_manager.get_conkers(victim_model)
                        )
                        added_nodes.add(victim)
                    # TODO: render headlines correctly;
                    #       I want to do this by refactoring PageGeneratorPlugin and using its code to render headlines,
                    #       then stripping the html using `''.join(xml.etree.ElementTree.fromstring(text).itertext())`
                    #       But this is waiting on Jamie's improvements to pseudonym rendering...
                    net.add_edge(killer_searchable, victim_searchable,
                                 label=e.datetime.strftime(DATETIME_FORMAT),
                                 color=get_color(
                                     victim_model.get_pseudonym(e.assassins.get(victim, 0)),
                                     is_police=victim_model.is_police,
                                     incompetent=competency_manager.is_inco_at(victim_model, e.datetime),
                                     is_wanted=wanted_manager.is_player_wanted(victim, e.datetime)
                                 ),
                                 title=f"[{e.datetime.strftime(DATETIME_FORMAT)}] {e.headline}"
                    )
            with open(os.path.join(WEBPAGE_WRITE_LOCATION, KILLTREE_PATH), "w+", encoding="utf-8") as F:
                F.write(net.generate_html())
            killtree_embed = KILLTREE_EMBED
        except ModuleNotFoundError:
            killtree_embed = ""
            components.append(Label("[WARNING] [SCORING] Module `pyvis` not found -- skipping kill tree visualisation."))
        except Exception as err:
            killtree_embed = ""
            components.append(Label(f"[WARNING] [SCORING] Error occured while generating kill tree visualisation ({err})"
                                    f" -- skipping."))


        with open(os.path.join(WEBPAGE_WRITE_LOCATION, "stats.html"), "w+", encoding="utf-8") as F:
            F.write(
                STATS_PAGE_TEMPLATE.format(
                    YEAR=get_now_dt().year,
                    TABLE=table_str,
                    KILLTREE=killtree_embed
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
    k: kills -- excludes kills of police, and of players who had already died when the kill was made
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

    def on_page_generate(self, _) -> List[HTMLComponent]:
        # don't generate open season page if open season hasn't started!
        open_season_start = timestamp_to_dt(self.gsdb_get("Start"))
        if not open_season_start or open_season_start >= get_now_dt():
            return []

        # also don't generate if formula is invalid
        formula = self.gsdb_get("Formula")
        if not self.formula_is_valid(formula):
            return [Label("[WARNING] [SCORING] Invalid scoring formula -- skipping openseason page!")]

        # need to include hidden assassins so that resurrecting as police doesn't stop kills counting
        score_manager = ScoreManager(ASSASSINS_DATABASE.get_identifiers(include=lambda a: not a.is_police,
                                                                        include_hidden=lambda a: not a.is_police),
                                     formula=formula,
                                     bonuses={
                                         ident: self.aps_get(ident, "Bonus")
                                         for ident in ASSASSINS_DATABASE.get_identifiers()
                                     })
        events = sorted(EVENTS_DATABASE.events.values(),
                        key=lambda e: e.datetime)
        for e in events:
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

        return [Label("[SCORING] Success!")]

