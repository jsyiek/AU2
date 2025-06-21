from AU2.database.model import Event
from AU2.plugins.sanity_checks.MalformedPlayerCode import MalformedPlayerCode
from AU2.test.test_utils import plugin_test, dummy_event


class TestMalformedPlayerCode:

    @plugin_test
    def test_detect_malformed_closing_brackets(self):
        """Test detection of various malformed closing brackets."""
        sanity_check = MalformedPlayerCode()
        
        # Create an event with malformed police codes in headline
        event = dummy_event()
        event.headline = "Player [P123) killed [D456( in combat. Also [N789} was present."
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should detect 3 malformed codes
        assert len(suggestions) == 3
        
        # Check the suggestions
        suggestion_explanations = [s.explanation for s in suggestions]
        assert "Fix player code brackets: [P123) -> [P123]" in suggestion_explanations
        assert "Fix player code brackets: [D456( -> [D456]" in suggestion_explanations
        assert "Fix player code brackets: [N789} -> [N789]" in suggestion_explanations

    @plugin_test
    def test_detect_malformed_in_reports(self):
        """Test detection of malformed police codes in reports."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "Normal headline"
        event.reports = [
            ("assassin1", 0, "I saw [P123) do something suspicious."),
            ("assassin2", 0, "The target [D456{ tried to escape."),
            ("assassin3", 0, "This is a normal report with [P123] correct code.")
        ]
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should detect 2 malformed codes (the third report has correct code)
        assert len(suggestions) == 2
        
        suggestion_explanations = [s.explanation for s in suggestions]
        assert "Fix player code brackets: [P123) -> [P123]" in suggestion_explanations
        assert "Fix player code brackets: [D456{ -> [D456]" in suggestion_explanations

    @plugin_test
    def test_detect_indexed_pseudonym_malformed(self):
        """Test detection of malformed indexed pseudonym codes like [P123_2)."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "Player used pseudonym [P123_2) in the attack."
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        assert len(suggestions) == 1
        assert suggestions[0].explanation == "Fix player code brackets: [P123_2) -> [P123_2]"

    @plugin_test
    def test_no_false_positives_for_correct_codes(self):
        """Test that correctly formatted codes don't trigger suggestions."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "Player [P123] killed [D456] while [N789] watched."
        event.reports = [
            ("assassin1", 0, "I used [P123_0] pseudonym correctly."),
            ("assassin2", 0, "The target [D456] and witness [N789] were there.")
        ]
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should detect no malformed codes
        assert len(suggestions) == 0

    @plugin_test
    def test_fix_malformed_codes(self):
        """Test that malformed codes are correctly fixed."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "Player [P123) killed target."
        event.reports = [
            ("assassin1", 0, "I saw [D456{ running away."),
            ("assassin2", 0, "Normal report.")
        ]
        
        # Get suggestions
        suggestions = sanity_check.suggest_event_fixes(event)
        suggestion_ids = [s.identifier for s in suggestions]
        
        # Apply fixes
        sanity_check.fix_event(event, suggestion_ids)
        
        # Check that codes were fixed
        assert event.headline == "Player [P123] killed target."
        assert event.reports[0][2] == "I saw [D456] running away."
        assert event.reports[1][2] == "Normal report."  # Unchanged

    @plugin_test
    def test_mixed_correct_and_malformed(self):
        """Test handling of mixed correct and malformed codes."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "Player [P123] killed [D456) while [N789] and [P321{ watched."
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should detect only the 2 malformed codes, not the correct ones
        assert len(suggestions) == 2
        
        suggestion_explanations = [s.explanation for s in suggestions]
        assert "Fix player code brackets: [P123] -> [P123]" not in suggestion_explanations  # Correct code
        assert "Fix player code brackets: [D456) -> [D456]" in suggestion_explanations
        assert "Fix player code brackets: [P321{ -> [P321]" in suggestion_explanations

    @plugin_test
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        # Test with various malformed endings
        event.headline = "Codes: [P1) [D22( [N333} [P4444~ [D55555! [N666666@"
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should detect all 6 malformed codes
        assert len(suggestions) == 6
        
        # Apply fixes
        suggestion_ids = [s.identifier for s in suggestions]
        sanity_check.fix_event(event, suggestion_ids)
        
        # All should be corrected to proper closing brackets
        expected = "Codes: [P1] [D22] [N333] [P4444] [D55555] [N666666]"
        assert event.headline == expected

    @plugin_test
    def test_left_side_bracket_mistakes(self):
        """Test detection of left-side bracket mistakes."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "Player (P123] killed {D456] while }N789] watched."
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should detect 3 malformed codes with wrong opening brackets
        assert len(suggestions) == 3
        
        suggestion_explanations = [s.explanation for s in suggestions]
        assert "Fix player code brackets: (P123] -> [P123]" in suggestion_explanations
        assert "Fix player code brackets: {D456] -> [D456]" in suggestion_explanations
        assert "Fix player code brackets: }N789] -> [N789]" in suggestion_explanations

    @plugin_test
    def test_parentheses_instead_of_brackets(self):
        """Test detection when parentheses are used instead of brackets."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "Player (P123) killed (D456) in combat."
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should detect 2 codes using parentheses instead of brackets
        assert len(suggestions) == 2
        
        suggestion_explanations = [s.explanation for s in suggestions]
        assert "Fix player code brackets: (P123) -> [P123]" in suggestion_explanations
        assert "Fix player code brackets: (D456) -> [D456]" in suggestion_explanations

    @plugin_test
    def test_mixed_bracket_types(self):
        """Test detection of mixed bracket types."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "Codes: {P123) (D456} [N789) {P321]"
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should detect all 4 mixed bracket codes
        assert len(suggestions) == 4
        
        suggestion_explanations = [s.explanation for s in suggestions]
        assert "Fix player code brackets: {P123) -> [P123]" in suggestion_explanations
        assert "Fix player code brackets: (D456} -> [D456]" in suggestion_explanations
        assert "Fix player code brackets: [N789) -> [N789]" in suggestion_explanations
        assert "Fix player code brackets: {P321] -> [P321]" in suggestion_explanations

    @plugin_test
    def test_missing_brackets_isolated_codes(self):
        """Test detection of missing brackets on isolated codes."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "Player P123 killed D456. Witness N789 saw it."
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should detect 3 codes missing brackets
        assert len(suggestions) == 3
        
        suggestion_explanations = [s.explanation for s in suggestions]
        assert "Fix player code brackets: P123 -> [P123]" in suggestion_explanations
        assert "Fix player code brackets: D456 -> [D456]" in suggestion_explanations
        assert "Fix player code brackets: N789 -> [N789]" in suggestion_explanations

    @plugin_test
    def test_no_false_positives_embedded_codes(self):
        """Test that codes embedded in words don't trigger false positives."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "The building P123ABC and room D456XYZ were checked."
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should not detect any codes since they're embedded in other text
        assert len(suggestions) == 0

    @plugin_test
    def test_preserve_outer_brackets(self):
        """Test that outer brackets are preserved while fixing inner brackets."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "Context ([P120)] and ({D456}) and {[N789)}."
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should detect nested bracket issues and preserve outer context
        assert len(suggestions) == 2  # ([P120)] is correct, others need fixes
        
        suggestion_explanations = [s.explanation for s in suggestions]
        assert "Fix player code brackets: ({D456}) -> ([D456])" in suggestion_explanations
        assert "Fix player code brackets: {[N789)} -> {[N789]}" in suggestion_explanations
        
        # Apply fixes
        suggestion_ids = [s.identifier for s in suggestions]
        sanity_check.fix_event(event, suggestion_ids)
        
        # Check that outer brackets are preserved
        assert "([P120])" in event.headline  # Should remain unchanged
        assert "([D456])" in event.headline  # Outer parens preserved
        assert "{[N789]}" in event.headline   # Outer braces preserved

    @plugin_test
    def test_simple_bracket_fixes_without_context(self):
        """Test simple bracket fixes without outer context."""
        sanity_check = MalformedPlayerCode()
        
        event = dummy_event()
        event.headline = "Simple cases: [P123) and (D456] and {N789}."
        
        suggestions = sanity_check.suggest_event_fixes(event)
        
        # Should fix all three to square brackets
        assert len(suggestions) == 3
        
        suggestion_explanations = [s.explanation for s in suggestions]
        assert "Fix player code brackets: [P123) -> [P123]" in suggestion_explanations
        assert "Fix player code brackets: (D456] -> [D456]" in suggestion_explanations
        assert "Fix player code brackets: {N789} -> [N789]" in suggestion_explanations

    @plugin_test
    def test_empty_and_minimal_cases(self):
        """Test with empty strings and minimal cases."""
        sanity_check = MalformedPlayerCode()
        
        # Empty event
        event = dummy_event()
        suggestions = sanity_check.suggest_event_fixes(event)
        assert len(suggestions) == 0
        
        # Event with no player codes
        event.headline = "No player codes here."
        event.reports = [("assassin1", 0, "Also no codes.")]
        suggestions = sanity_check.suggest_event_fixes(event)
        assert len(suggestions) == 0