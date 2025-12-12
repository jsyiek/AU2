import re
from typing import List, Dict, Set

from AU2.database.model import Event
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.html_components import HTMLComponent
from AU2.plugins.sanity_checks.model.SanityCheck import SanityCheck
from AU2.plugins.sanity_checks.model.SanityCheck import Suggestion

DX_NX_PATTERN = re.compile(r"(\[[DNLV](\d+)\])")

class PlayerNotDead(SanityCheck):
    """
    Finds and detects cases where [VX], [LX], [DX] and [NX] appear,
    despite the player being alive.
    """

    identifier = "Player_Not_Dead"

    def _find_incorrect(self, string: str, dead_secret_ids: Set[str], fixes: Dict[str, str]):
        # matches either [VX], [LX], [DX] or [NX]
        for match in DX_NX_PATTERN.findall(string):
            X = match[1]
            if X not in dead_secret_ids:
                fixes[match[0]] = X

    def _gather_incorrect(self, e: Event):
        dead_secret_ids = set(ASSASSINS_DATABASE.get(victim_id)._secret_id for _, victim_id in e.kills)
        output = {}
        for (_, _, report) in e.reports:
            self._find_incorrect(report, dead_secret_ids, output)
        self._find_incorrect(e.headline, dead_secret_ids, output)
        return output

    def suggest_event_fixes(self, e: Event) -> List[Suggestion]:
        suggestions = []
        to_fix = self._gather_incorrect(e)
        for original, secret_id in to_fix.items():
            assassin_match = lambda a: a._secret_id == secret_id
            alist = ASSASSINS_DATABASE.get_filtered(include=assassin_match, include_hidden=assassin_match)
            if len(alist) == 1:
                a = alist[0]
                suggestions.append(
                    Suggestion(
                        identifier=f"{original}_[P{secret_id}]",
                        explanation=f"{a.identifier} is not dead. Replace: {original} -> [P{secret_id}]"
                    )
                )
        return suggestions

    def fix_event(self, e: Event, suggestion_ids: List[str]) -> List[HTMLComponent]:
        for suggestion_str in suggestion_ids:
            original, replacement = suggestion_str.split("_")
            e.headline = e.headline.replace(original, replacement)
            for i, (assassin_id, pseudonym_id, report) in enumerate(e.reports):
                e.reports[i] = (assassin_id, pseudonym_id, report.replace(original, replacement))
        return []
