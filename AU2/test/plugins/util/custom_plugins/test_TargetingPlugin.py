import time

from typing import Dict, List

from AU2.database.model.database_utils import refresh_databases
from AU2.plugins.custom_plugins.TargetingPlugin import TargetingPlugin
from AU2.test.test_utils import plugin_test, some_players, MockGame


def valid_targets(num_players, targets):
    assert len(targets) == num_players
    assert all(len(t) == 3 for t in targets.values())
    return True


def teams_respected(targets: Dict[str, List[str]], teams: List[List[str]]) -> bool:
    for team in teams:
        for member in team:
            for target in targets.get(member, ()):
                assert target not in team
    return True


def seeds_respected(targets: Dict[str, List[str]], seeds: List[str]) -> bool:
    for seed1 in seeds:
        for seed2 in seeds:
            assert seed2 not in targets[seed1]
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

        game.assassin(p[0]).kills(p[1]).then() \
            .assassin(p[2]).kills(p[3]).then() \
            .assassin(p[4]).kills(p[5]).then() \
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
            .assassin(p[20]).with_accomplices(p[2], p[3]).kills(p[180]).then() \
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

    @plugin_test
    def test_many_kills_in_event(self):
        num_players = 250
        p = some_players(num_players)
        game = MockGame().having_assassins(p)

        kills = 5
        game.assassin(p[0]).kills(*p[1:(1+kills)])

        plugin = TargetingPlugin()
        start = time.perf_counter()
        targets = plugin.compute_targets([])
        perf = time.perf_counter() - start

        assert valid_targets(num_players - kills, targets)

        # test passes only if calculation took a reasonable amount of time
        assert perf < 1.0

    @plugin_test
    def test_no_team_targets(self):
        """Test targeting when players are all in teams of sizes up to 4"""
        num_players = 250
        p = some_players(num_players)
        plugin = TargetingPlugin()
        for team_size in range(2, 5):
            refresh_databases()
            game = MockGame().having_assassins(p)
            # group consecutive players into teams
            teams = [[x + " identifier" for x in p[i: i+team_size]] for i in range(0, num_players, team_size)]
            plugin.answer_set_teams({
                plugin.html_ids["Teams"]: teams
            })

            # check that initial graph respects teams
            targs = plugin.compute_targets([])

            assert valid_targets(num_players, targs)
            assert teams_respected(targs, teams)

            # add a moderate number of deaths and check teams still respected
            for i in range(50):
                game.assassin(p[i]).kills(p[num_players-1-i])
            targs = plugin.compute_targets([])
            assert valid_targets(len(game.get_remaining_players()), targs)
            assert teams_respected(targs, teams)

    @plugin_test
    def test_mentors(self):
        """Test of scenario where we have a few seeds 'mentoring' new players"""
        num_players = 250
        p = some_players(num_players)
        game = MockGame().having_assassins(p)
        num_seeds = 10
        plugin = TargetingPlugin()
        seeds = [x + " identifier" for x in p[:num_seeds]]
        plugin.answer_set_seeds({
            plugin.html_ids["Seeds"]: seeds
        })
        teams = [[p[i] + " identifier", p[num_seeds + 1] + " identifier"] for i in range(num_seeds)]
        plugin.answer_set_teams({
            plugin.html_ids["Teams"]: teams
        })

        # check initial targets
        targs = plugin.compute_targets([])
        assert valid_targets(num_players, targs)
        assert teams_respected(targs, teams)
        assert seeds_respected(targs, seeds)

        # add a moderate number of deaths and check teams still respected
        for i in range(50):
            game.assassin(p[i]).kills(p[num_players - 1 - i])
        targs = plugin.compute_targets([])
        assert valid_targets(len(game.get_remaining_players()), targs)
        assert teams_respected(targs, teams)
        assert seeds_respected(targs, seeds)

        # add many more deaths and check seeds still respected (but accept if other teams aren't)
        for i in range(100):
            game.assassin(p[i]).kills(p[num_players - 1 - i])
        targs = plugin.compute_targets([])
        assert valid_targets(len(game.get_remaining_players()), targs)
        assert seeds_respected(targs, seeds)
