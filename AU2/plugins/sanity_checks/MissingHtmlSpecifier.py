from typing import List

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.Label import Label
from AU2.plugins.sanity_checks.model.SanityCheck import SanityCheck
from AU2.plugins.sanity_checks.model.SanityCheck import Suggestion
from AU2.plugins.util.game import HTML_REPORT_PREFIX


class MissingHtmlSpecifier(SanityCheck):

    identifier = "Missing_HTML_Specifier"

    html_indicators = [
        "<br>",
        "<b>",
        "<html>",
        "<em>"
    ]

    def suggest_event_fixes(self, e: Event) -> List[Suggestion]:
        suggestions = []
        for i, (assassin, pseudonym_id, report) in enumerate(e.reports):
            if any(h in report for h in self.html_indicators) and HTML_REPORT_PREFIX not in report:
                name = ASSASSINS_DATABASE.assassins[assassin].real_name
                suggestions.append(
                    Suggestion(
                        explanation=f"Enable HTML in {name}'s report (id={i})",
                        data={
                            "report": i
                        }
                    )
                )
        return suggestions

    def fix_event(self, e: Event, suggestion_data: List[dict]) -> List[HTMLComponent]:
        suggestion_ids = sorted([data["report"] for data in suggestion_data])
        fix_ptr = 0
        labels = []
        for i, (assassin, pseudonym_id, report) in enumerate(e.reports):
            if i == suggestion_ids[fix_ptr]:
                fix_ptr += 1
                report = HTML_REPORT_PREFIX + report
                e.reports[i] = (assassin, pseudonym_id, report)
                name = ASSASSINS_DATABASE.assassins[assassin].real_name
                labels.append(
                    Label(f"({e.identifier}) Enabled HTML for {name}'s report.")
                )
            if fix_ptr == len(suggestion_ids):
                break
        return labels
