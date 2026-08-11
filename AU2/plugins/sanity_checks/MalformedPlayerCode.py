import re
from typing import List, Dict

from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.plugins.sanity_checks.model.SanityCheck import SanityCheck
from AU2.plugins.sanity_checks.model.SanityCheck import Suggestion


class MalformedPlayerCode(SanityCheck):
    """
    Detects and fixes malformed player codes in event headlines and reports.
    
    Player codes should use the format [PX], [DX], or [NX] where X is a number.
    Some codes may be contextually wrapped in parentheses as ([CODE]).
    
    Detects various bracket mistakes including:
    - Mismatched brackets: [P123) -> [P123]
    - Wrong bracket types: (P123) -> [P123] or {P123} -> [P123]
    - Mixed bracket patterns: ([P123)] -> ([P123])
    - Missing brackets on isolated codes: P123 -> [P123]
    - Contextual corrections: [(P123)] -> ([P123])
    """

    identifier = "Malformed_Player_Code"

    def _find_malformed_codes(self, string: str, fixes: Dict[str, str]):
        """
        Find malformed player codes in the string and add corrections to fixes dict.
        
        Args:
            string: Text to search for malformed player codes
            fixes: Dictionary to store original -> corrected mappings
        """
        # Regex to match player codes: [P/D/N][digits][optional_index]
        # Captures surrounding brackets, core code, and closing brackets
        pattern = r"([\(\{\[]*)([PND]\d+(?:_\d+)?)([\]\)\}]*)"
        
        for match in re.finditer(pattern, string):
            prefix_brackets = match.group(1)  # Opening brackets
            player_code = match.group(2)      # The player code itself
            suffix_brackets = match.group(3)  # Closing brackets
            full_match = match.group(0)
            
            # Skip unbracketed codes that aren't clearly isolated
            if not prefix_brackets and not suffix_brackets:
                if not self._is_isolated_code(string, match.start(), match.end()):
                    continue
            
            # Determine if this needs fixing
            needs_fixing = False
            corrected_code = None
            
            # Case 1: No brackets at all on an isolated code
            if not prefix_brackets and not suffix_brackets:
                corrected_code = f"[{player_code}]"
                needs_fixing = True
            
            # Case 2: Has brackets but they're not square brackets
            elif prefix_brackets or suffix_brackets:
                # Check if it's properly formatted [CODE]
                if prefix_brackets == '[' and suffix_brackets == ']':
                    # Already correct
                    continue
                # Check if it has the correct format: ([CODE])
                elif full_match == f"([{player_code}])":
                    # This is valid - outer parentheses with inner square brackets
                    continue
                # Check for patterns that should be ([CODE]) format:
                # - [(CODE)] - reversed brackets
                # - [(CODE] - incomplete reversed  
                # - ([CODE] - incomplete correct start
                # - ([CODE)] - mixed brackets (paren-bracket start, bracket-paren end)
                elif (full_match.startswith('[(') or 
                      full_match.startswith('([') or 
                      (full_match.startswith('[') and full_match.endswith(')]'))):
                    # This looks like it should be ([CODE]) format
                    corrected_code = f"([{player_code}])"
                    needs_fixing = True
                # Check for simple bracket mismatches like [CODE) or (CODE] 
                elif ((full_match.startswith('[') and full_match.endswith(')')) or 
                      (full_match.startswith('(') and full_match.endswith(']'))):
                    # Simple bracket mismatch - fix to [CODE]
                    corrected_code = f"[{player_code}]"
                    needs_fixing = True
                else:
                    # Default: replace with square brackets only
                    corrected_code = f"[{player_code}]"
                    needs_fixing = True
            
            # Add to fixes if malformed
            if needs_fixing and corrected_code and full_match != corrected_code:
                fixes[full_match] = corrected_code

    def _is_isolated_code(self, string: str, start_pos: int, end_pos: int) -> bool:
        """Check if a player code is isolated (not part of a larger word)."""
        before_char = string[start_pos - 1] if start_pos > 0 else ' '
        after_char = string[end_pos] if end_pos < len(string) else ' '
        
        # Skip if it's likely part of a larger word/identifier
        if before_char.isalnum() or after_char.isalnum():
            return False
            
        # Only consider isolated if surrounded by proper separators
        return before_char in ' .,;:!?' and after_char in ' .,;:!?'

    def _gather_fixes(self, e: Event):
        """Gather all needed fixes for an event."""
        output = {}
        # Check headline
        self._find_malformed_codes(e.headline, output)
        # Check all reports
        for (_, _, report) in e.reports:
            self._find_malformed_codes(report, output)
        return output

    def suggest_event_fixes(self, e: Event) -> List[Suggestion]:
        suggestions = []
        fixes = self._gather_fixes(e)
        for original, replacement in fixes.items():
            suggestions.append(
                Suggestion(
                    identifier=f"{original}_{replacement}",
                    explanation=f"Fix player code brackets: {original} -> {replacement}"
                )
            )
        return suggestions

    def fix_event(self, e: Event, suggestion_ids: List[str]) -> List[HTMLComponent]:
        for suggestion_str in suggestion_ids:
            # suggestion_str format: "{original}_{replacement}"
            original, replacement = suggestion_str.split("_", 1)
            # Fix headline
            e.headline = e.headline.replace(original, replacement)
            # Fix all reports
            for i, (assassin_id, pseudonym_id, report) in enumerate(e.reports):
                e.reports[i] = (assassin_id, pseudonym_id, report.replace(original, replacement))
        return []
