import re
from typing import List, Dict

from AU2.database.model import Event
from AU2.html_components import HTMLComponent
from AU2.plugins.sanity_checks.model.SanityCheck import SanityCheck
from AU2.plugins.sanity_checks.model.SanityCheck import Suggestion


class MalformedPlayerCode(SanityCheck):
    """
    Finds and detects cases where player pseudonym/name codes like [PX], [DX], [NX] have
    incorrect brackets and suggests corrections, preserving outer context.
    
    Detects various bracket mistakes including:
    - Wrong closing bracket: [P123) -> [P123]
    - Wrong opening bracket: (P123] -> [P123] 
    - Mixed brackets: {P123) -> [P123]
    - Missing brackets: P123] -> [P123]
    - Parentheses instead of brackets: (P123) -> [P123]
    - Preserves outer context: ([P120)] -> ([P120])
    """

    identifier = "Malformed_Player_Code"

    def _find_malformed_codes(self, string: str, fixes: Dict[str, str]):
        """
        Find malformed player pseudonym/name codes in the given string and add corrections to fixes dict.
        
        Detects various bracket mistakes while preserving outer context:
        - Wrong closing bracket: [P123) -> [P123]
        - Wrong opening bracket: (P123] -> [P123]
        - Mixed brackets: {P123) -> [P123]
        - Missing opening bracket: P123] -> [P123]
        - Parentheses instead: (P123) -> [P123]
        - Mixed outer/inner brackets: ([P123)] -> [P123]
        """
        # Pattern to match player codes with various bracket configurations
        # Captures any surrounding brackets and the player code
        pattern = r"([\(\{\[]*)([PND]\d+(?:_\d+)?)([\]\)\}]*)"
        
        for match in re.finditer(pattern, string):
            prefix_brackets = match.group(1)  # Opening brackets
            player_code = match.group(2)      # The player code itself
            suffix_brackets = match.group(3)  # Closing brackets
            full_match = match.group(0)
            
            # Skip if no brackets at all and not clearly isolated
            if not prefix_brackets and not suffix_brackets:
                before_pos = match.start()
                after_pos = match.end()
                
                before_char = string[before_pos - 1] if before_pos > 0 else ' '
                after_char = string[after_pos] if after_pos < len(string) else ' '
                
                # Skip if it's likely part of a larger word/identifier
                if before_char.isalnum() or after_char.isalnum():
                    continue
                    
                # Only suggest brackets if it's clearly a standalone code
                if not (before_char in ' .,;:!?' and after_char in ' .,;:!?'):
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
                elif (full_match.startswith('[') or full_match.startswith('([')) and ('(' in full_match or ')' in full_match):
                    # This looks like it should be ([CODE]) format
                    corrected_code = f"([{player_code}])"
                    needs_fixing = True
                else:
                    # Default: replace with square brackets only
                    corrected_code = f"[{player_code}]"
                    needs_fixing = True
            
            # Add to fixes if malformed
            if needs_fixing and corrected_code and full_match != corrected_code:
                fixes[full_match] = corrected_code

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