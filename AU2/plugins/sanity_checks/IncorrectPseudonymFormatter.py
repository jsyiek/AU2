import re
from typing import List, Dict

from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.plugins.sanity_checks.model.SanityCheck import SanityCheck
from AU2.plugins.sanity_checks.model.SanityCheck import Suggestion

class IncorrectPseudonymFormatter(SanityCheck):

    identifier = "Incorrect_Pseudonym_Formatter"

    def _fix(self, string: str, fixes: Dict[str, str]):
        search_pattern = r"\[([0-9]+)\]"
        for match in re.findall(search_pattern, string):
            fixes[f"[{match}]"] = f"[P{match}]"

    def _gather_fixes(self, e: Event):
        output = {}
        for (_, _, report) in e.reports:
            self._fix(report, output)
        self._fix(e.headline, output)
        return output

    def suggest_event_fixes(self, e: Event) -> List[Suggestion]:
        suggestions = []
        fixes = self._gather_fixes(e)
        for original, replacement in fixes.items():
            suggestions.append(
                Suggestion(
                    identifier=f"{original}_{replacement}",
                    explanation=f"Replace: {original} -> {replacement}"
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
