from AU2.plugins.custom_plugins.TargetingPlugin import TargetingPlugin
from AU2.test.test_utils import plugin_test, some_players, MockGame


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
    def test_ignores_city_watch(self):
        num_players = 250
        p = some_players(num_players)
        game = MockGame().having_assassins(p)

        game.assassin(p[0]).and_these(p[1], p[20], p[45], p[135]).are_city_watch() \
            .assassin(p[20]).with_accomplices(p[2], p[3]).kills(p[180]) \
            .assassin(p[25]).kills(p[20])

        plugin = TargetingPlugin()
        targets = plugin.compute_targets([])

        # 5 city watch, 1 full player dead
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
