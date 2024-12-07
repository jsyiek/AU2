import re
from typing import List, Dict

from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.plugins.sanity_checks.model.SanityCheck import SanityCheck
from AU2.plugins.sanity_checks.model.SanityCheck import Suggestion


class IncorrectPseudonymFormatter(SanityCheck):
    """
    Finds and detects cases where the umpire writes pseudonysm as
    [X] instead of [PX] and corrects them.
    """

    identifier = "Incorrect_Pseudonym_Formatter"

    def _fix(self, string: str, fixes: Dict[str, str]):
        # Matches any number of white space, one word, then [X], then one word and space
        search_pattern = r"(\S*[^\w\n]*)\[([0-9]+)\]([^\w\n]*\S*)"
        for match in re.findall(search_pattern, string):
            fixes[f"{match[0]}[{match[1]}]{match[2]}"] = f"{match[0]}[P{match[1]}]{match[2]}"

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
