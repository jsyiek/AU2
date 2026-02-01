import random
import math
from typing import Dict

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.plugins.custom_plugins.ScoringPlugin import ScoringPlugin
from AU2.plugins.util.ScoreManager import ScoreManager
from AU2.test.test_utils import MockGame, some_players, plugin_test, dummy_event


class TestScoringPlugin:

    def get_manager(self, mockGame, perma_death: bool = True, filter_city_watch = True) -> ScoreManager:
        m = ScoreManager(assassin_ids=[name + " identifier" for name in mockGame.all_assassins
                                       if not (filter_city_watch and mockGame.assassin_model(name).is_city_watch)],
                         perma_death=perma_death)
        for e in sorted(EVENTS_DATABASE.events.values(), key=lambda e: e.datetime):
            m.add_event(e)
        return m

    def random_attempts(self, game: MockGame) -> Dict[str, int]:
        """
        Adds random attempts to `game` and returns a dict of the correct number of attempts for each assassin
        """
        players = game.get_remaining_players()
        n_players = len(players)
        n_events = abs(math.floor(random.normalvariate(n_players, n_players/3)))
        attempts_map = {}
        for i in range(n_events):
            attempters = set(random.choices(players, k=math.ceil(random.expovariate(1))))
            others = set(random.choices(players, k=math.ceil(random.expovariate(1/3)))) - attempters
            game.add_attempts(*attempters, others=list(others))
            for a in attempters:
                attempts_map[a] = attempts_map.get(a, 0) + 1
        return attempts_map

    @plugin_test
    def test_scoring_params_1(self):
        """
        Test game 1: chain of kills
        Kill tree looks like
        n-1 -> n-2 -> ... -> 1 -> 0
        """
        n = 50
        p = some_players(n)
        game = MockGame().having_assassins(p)
        idents = [name + " identifier" for name in p]

        attempts_map = self.random_attempts(game)

        # add chain of kills
        for i in range(1, n):
            game.assassin(p[i]).kills(p[i-1]).new_datetime()

        # hide some players (not player n-1) -- their kills should still be counted!
        for i in random.choices(range(0, n-1), k = 1 + n // 10):
            game.assassin(p[i]).is_hidden()

        manager = self.get_manager(game)
        # kills should equal 1 for each except player 0
        for i in range(1, n):
            assert manager._kills(idents[i]) == 1
        assert manager._kills(idents[0]) == 0

        # conker should be 0 for player 0 (no kills),
        # then 1 for player 1, increasing by 1 as we go up the chain of kills
        # i.e. should equal the index of the player in this mock game
        for i in range(n):
            assert manager._conkers(idents[i]) == i

        # check attempts manager tracks attempts correctly
        for i in range(n):
            assert manager._attempts(idents[i]) == attempts_map.get(p[i], 0)

        # only one player should be alive in this game, namely p[n-1]
        assert manager.live_assassins == {idents[n-1]}

    @plugin_test
    def test_scoring_params_2(self):
        """
        Test game 2: binary kill tree
        kill tree looks like
        0 -> 1 -> 3 -> 7
          |    |    |
          |    |    -> 8
          |    |
          |    -> 4 -> 9
          |         |
          |         -> 10
          |
          -> 2 -> 5 -> 11
               |    |
               |    -> 12
               |
               -> 6 -> 13
                    |
                    -> 14
        """
        n = 15
        p = some_players(n)
        game = MockGame().having_assassins(p)
        idents = [name + " identifier" for name in p]

        attempts_map = self.random_attempts(game)

        # mix of kills in same events and across events,
        game.assassin(p[6]).kills(p[13], p[14]).new_datetime()
        game.assassin(p[5]).kills(p[11]).assassin(p[5]).kills(p[12]).new_datetime()

        game.assassin(p[2]).kills(p[5]).new_datetime()

        game.assassin(p[4]).kills(p[9], p[10]).new_datetime()
        game.assassin(p[3]).kills(p[7]).assassin(p[3]).kills(p[8]).new_datetime()

        game.assassin(p[2]).kills(p[6]).new_datetime()
        game.assassin(p[1]).kills(p[3], p[4]).new_datetime()

        game.assassin(p[0]).kills(p[1], p[2]).new_datetime()

        # hide some players (not 0) -- their kills should still be counted!
        for i in random.choices(range(1, n), k = 1 + n // 5):
            game.assassin(p[i]).is_hidden()

        manager = self.get_manager(game)

        # check kills are counted correctly
        for i in range(0, 7):
            assert manager._kills(idents[i]) == 2
        for i in range(7, 15):
            assert manager._kills(idents[i]) == 0

        # check conkers calculated correctly
        assert manager._conkers(idents[0]) == 14
        for i in range(1, 3):
            assert manager._conkers(idents[i]) == 6
        for i in range(3, 6):
            assert manager._conkers(idents[i]) == 2
        for i in range(7, 15):
            assert manager._conkers(idents[i]) == 0

        # check attempts counted correctly
        for i in range(15):
            assert manager._attempts(idents[i]) == attempts_map.get(p[i], 0)

        # only one player should be alive in this game, namely p[0]
        assert manager.live_assassins == {idents[0]}

    @plugin_test
    def test_looped_killtree(self):
        """
        Tests whether conkers are calculated correctly when loops are involved in the kill graph
        (with perma-death turned off)
        Kill graph used is
            0 <-> 1 -> 2
                 /|\   |
                  |   \|/
                  4 <- 3
        """
        p = some_players(5)
        idents = [name + " identifier" for name in p]
        game = MockGame().having_assassins(p)

        # construct kill graph
        game.assassin(p[3]).kills(p[4]).new_datetime()
        game.assassin(p[2]).kills(p[3]).new_datetime()
        game.assassin(p[1]).kills(p[2]).new_datetime()
        game.assassin(p[4]).kills(p[1]).new_datetime()
        game.assassin(p[0]).kills(p[1]).new_datetime()
        game.assassin(p[1]).kills(p[0]).new_datetime()

        manager = self.get_manager(game, perma_death=False)

        # check kills are counted correctly
        for i in range(0, 5):
            if i == 1:
                assert manager._kills(idents[i]) == 2
            else:
                assert manager._kills(idents[i]) == 1

        # check conkers calculated correctly
        # note that players do not get conkers from themselves!
        # (could change this as a revenge bonus?)
        for i in range(5):
            assert manager._conkers(idents[i]) == 4

        # check all players still counted as live (since no perma-death)
        assert manager.live_assassins == set(idents)

    @plugin_test
    def test_double_death_and_city_watch(self):
        """
        Kill tree is
                 7 -> 6
                      |
                     \|/
            4 -> 0 -> 1 -> 3
                     /|\
                      |
                 5 -> 2
        where 3 and 7 are members of the city watch and 0 killed 1 first.
        (this models the situation where a player went wanted then three people killed them in quick succession)
        """
        n = 8
        p = some_players(n)
        game = MockGame().having_assassins(p)
        idents = [name + " identifier" for name in p]

        game.assassin(p[3]).with_accomplices(p[7]).are_city_watch()
        game.assassin(p[1]).kills(p[3]).new_datetime()
        game.assassin(p[0]).kills(p[1]).new_datetime()
        game.assassin(p[2]).kills(p[1]).new_datetime()
        game.assassin(p[6]).kills(p[1]).new_datetime()
        game.assassin(p[5]).kills(p[2]).new_datetime()
        game.assassin(p[4]).kills(p[0]).new_datetime()
        game.assassin(p[7]).kills(p[6])

        manager = self.get_manager(game)

        # check kills are counted correctly
        for i in range(0, n):
            if i in {0, 4, 5}:
                assert manager._kills(idents[i]) == 1
            elif i in {3, 7}:
                continue  # we don't care about city watch kill counts
            else:
                assert manager._kills(idents[i]) == 0

        # check conkers are calculated correctly
        for i in range(0, n):
            if i in {0, 5}:
                assert manager._conkers(idents[i]) == 1
            elif i in {4}:
                assert manager._conkers(idents[i]) == 2
            elif i in {3, 7}:
                continue  # we don't care about city watch conkers
            else:
                assert manager._conkers(idents[i]) == 0

        # check the open season list is correct
        assert manager.live_assassins == {idents[4], idents[5]}
