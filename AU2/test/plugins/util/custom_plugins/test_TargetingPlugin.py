from AU2.plugins.custom_plugins.TargetingPlugin import TargetingPlugin
from AU2.test.test_utils import plugin_test, some_players, MockGame
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE


def valid_targets(num_players, targets):
    assert len(targets) == num_players
    assert all(len(t) == 3 for t in targets.values())
    return True


class TestTargetingPlugin:

    @plugin_test
    def test_require_minimum_8_players(self):
        """
        Targeting graph requires minimum 8 players
        """
        players = some_players(7)
        MockGame().having_assassins(players)
        assert TargetingPlugin().compute_targets([]) == {}

    @plugin_test
    def test_some_deaths(self):
        """
        A simple test for deaths
        """
        num_players = 53
        p = some_players(num_players)
        game = MockGame().having_assassins(p)

        plugin = TargetingPlugin()
        targets = plugin.compute_targets([])
        assert valid_targets(num_players, targets)

        game.assassin(p[0]).kills(p[1]) \
            .assassin(p[2]).kills(p[3]) \
            .assassin(p[4]).kills(p[5]) \
            .assassin(p[6]).kills(p[7])

        targets = plugin.compute_targets([])
        assert valid_targets(num_players - 4, targets)

    @plugin_test
    def test_lots_of_deaths(self):
        num_players = 250
        p = some_players(num_players)
        game = MockGame().having_assassins(p)

        plugin = TargetingPlugin()
        targets = plugin.compute_targets([])
        assert valid_targets(num_players, targets)

        for i in range(100):
            game.assassin(p[2 * i]).kills(p[2 * i + 1])

        targets = plugin.compute_targets([])
        assert valid_targets(num_players - 100, targets)

    @plugin_test
    def test_92_5_percent_deaths(self):
        """
        Robustness test. Eliminate 92.5% of the game
        """
        num_players = 200
        p = some_players(num_players)
        game = MockGame().having_assassins(p)

        plugin = TargetingPlugin()
        targets = plugin.compute_targets([])
        assert valid_targets(num_players, targets)

        it = 0
        for i in range(185):
            pl = game.get_remaining_players()
            it = (it + 1) % len(pl)
            targeter = pl[it]
            victim = pl[(it + 1) % len(pl)]
            game.assassin(targeter).kills(victim)

        targets = plugin.compute_targets([])
        assert valid_targets(num_players - 185, targets)

    @plugin_test
    def test_ignores_police(self):
        num_players = 250
        p = some_players(num_players)
        game = MockGame().having_assassins(p)

        game.assassin(p[0]).and_these(p[1], p[20], p[45], p[135]).are_police() \
            .assassin(p[20]).with_accomplices(p[2], p[3]).kills(p[180]) \
            .assassin(p[25]).kills(p[20])

        plugin = TargetingPlugin()
        targets = plugin.compute_targets([])

        # 5 police, 1 player dead
        assert valid_targets(num_players - 5 - 1, targets)

    @plugin_test
    def test_no_crash_when_double_kill(self):
        num_players = 250
        p = some_players(num_players)
        game = MockGame().having_assassins(p)
        for a in p[1:]:
            game.assassin(a).kills(p[0])

        plugin = TargetingPlugin()
        plugin.compute_targets([])

        # if doesn't crash, test passes

    @plugin_test
    def test_disable_seeds_config_option_available(self):
        """
        Test that the disable_seeds_for_updates configuration option is available and settable.
        """
        plugin = TargetingPlugin()
        
        # Test that the configuration export exists
        config_export_identifiers = [export.identifier for export in plugin.config_exports]
        assert "targeting_disable_update_seeding" in config_export_identifiers
        
        # Test that the default value is False
        disable_value = GENERIC_STATE_DATABASE.arb_state.get(plugin.identifier, {}).get("disable_seeds_for_updates", False)
        assert disable_value == False
        
        # Test that we can set the value to True
        GENERIC_STATE_DATABASE.arb_state.setdefault(plugin.identifier, {})["disable_seeds_for_updates"] = True
        stored_value = GENERIC_STATE_DATABASE.arb_state.get(plugin.identifier, {}).get("disable_seeds_for_updates", False)
        assert stored_value == True
        
        # Test that we can set it back to False
        GENERIC_STATE_DATABASE.arb_state[plugin.identifier]["disable_seeds_for_updates"] = False
        stored_value = GENERIC_STATE_DATABASE.arb_state.get(plugin.identifier, {}).get("disable_seeds_for_updates", False)
        assert stored_value == False

    @plugin_test
    def test_targeting_works_without_seeds(self):
        """
        Test that targeting works normally without seeds (ensuring our changes don't break basic functionality).
        """
        num_players = 25
        p = some_players(num_players)
        game = MockGame().having_assassins(p)
        
        plugin = TargetingPlugin()
        
        # Test with disable option False (default)
        GENERIC_STATE_DATABASE.arb_state.setdefault(plugin.identifier, {})["disable_seeds_for_updates"] = False
        
        targets_default = plugin.compute_targets([])
        assert valid_targets(num_players, targets_default)
        
        # Test with disable option True
        GENERIC_STATE_DATABASE.arb_state[plugin.identifier]["disable_seeds_for_updates"] = True
        
        targets_disabled = plugin.compute_targets([])
        assert valid_targets(num_players, targets_disabled)
        
        # Both should work identically when no seeds are set
        
        # Test that deaths work in both modes
        game.assassin(p[10]).kills(p[11])
        
        # With disabled seeds
        targets_after_disabled = plugin.compute_targets([])
        assert valid_targets(num_players - 1, targets_after_disabled)
        
        # Reset and test with enabled seeds (default)
        game = MockGame().having_assassins(p)
        GENERIC_STATE_DATABASE.arb_state[plugin.identifier]["disable_seeds_for_updates"] = False
        
        game.assassin(p[10]).kills(p[11])
        targets_after_enabled = plugin.compute_targets([])
        assert valid_targets(num_players - 1, targets_after_enabled)

    @plugin_test
    def test_ask_answer_methods_work(self):
        """
        Test that the ask and answer methods for the new configuration work correctly.
        """
        plugin = TargetingPlugin()
        
        # Test the ask method returns a checkbox
        components = plugin.ask_disable_update_seeding()
        assert len(components) == 1
        checkbox = components[0]
        assert checkbox.name == "Checkbox"
        
        # Test the answer method with True
        mock_response = {plugin.html_ids["Disable Update Seeding"]: True}
        result = plugin.answer_disable_update_seeding(mock_response)
        
        # Check that the value was stored
        stored_value = GENERIC_STATE_DATABASE.arb_state.get(plugin.identifier, {}).get("disable_seeds_for_updates", False)
        assert stored_value == True
        
        # Check return message
        assert len(result) == 1
        assert "disabled" in result[0].title
        
        # Test the answer method with False
        mock_response = {plugin.html_ids["Disable Update Seeding"]: False}
        result = plugin.answer_disable_update_seeding(mock_response)
        
        # Check that the value was updated
        stored_value = GENERIC_STATE_DATABASE.arb_state.get(plugin.identifier, {}).get("disable_seeds_for_updates", False)
        assert stored_value == False
        
        # Check return message
        assert len(result) == 1
        assert "enabled" in result[0].title
