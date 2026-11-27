import random
import math
from typing import Dict, List

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import Assassin
from AU2.plugins.custom_plugins.ScoringPlugin import ScoringPlugin
from AU2.plugins.util.ScoreManager import ScoreManager
from AU2.test.plugins.util.custom_plugins.test_CompetencyPlugin import get_competency_manager
from AU2.test.test_utils import MockGame, some_players, plugin_test, dummy_event


class TestScoringPlugin:

    def get_manager(self, mockGame, formula="", perma_death: bool = True, filter_city_watch = True, bonuses = {}) -> ScoreManager:
        m = ScoreManager(assassin_ids=[name + " identifier" for name in mockGame.all_assassins
                                       if not (filter_city_watch and mockGame.assassin_model(name).is_city_watch)],
                         perma_death=perma_death,
                         formula=formula,
                         bonuses=bonuses)
        for e in EVENTS_DATABASE.events_chronologically():
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
            game.assassin(p[i]).kills(p[i-1]).then().new_datetime()

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
        game.assassin(p[6]).kills(p[13], p[14]).then().new_datetime()
        game.assassin(p[5]).kills(p[11]).then().assassin(p[5]).kills(p[12]).then().new_datetime()

        game.assassin(p[2]).kills(p[5]).then().new_datetime()

        game.assassin(p[4]).kills(p[9], p[10]).then().new_datetime()
        game.assassin(p[3]).kills(p[7]).then().assassin(p[3]).kills(p[8]).then().new_datetime()

        game.assassin(p[2]).kills(p[6]).then().new_datetime()
        game.assassin(p[1]).kills(p[3], p[4]).then().new_datetime()

        game.assassin(p[0]).kills(p[1], p[2]).then().new_datetime()

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
        game.assassin(p[3]).kills(p[4]).then().new_datetime()
        game.assassin(p[2]).kills(p[3]).then().new_datetime()
        game.assassin(p[1]).kills(p[2]).then().new_datetime()
        game.assassin(p[4]).kills(p[1]).then().new_datetime()
        game.assassin(p[0]).kills(p[1]).then().new_datetime()
        game.assassin(p[1]).kills(p[0]).then().new_datetime()

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
        game.assassin(p[1]).kills(p[3]).then().new_datetime()
        game.assassin(p[0]).kills(p[1]).then().new_datetime()
        game.assassin(p[2]).kills(p[1]).then().new_datetime()
        game.assassin(p[6]).kills(p[1]).then().new_datetime()
        game.assassin(p[5]).kills(p[2]).then().new_datetime()
        game.assassin(p[4]).kills(p[0]).then().new_datetime()
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

    @plugin_test
    def test_standings_example(self):
        """Test that standings are generated correctly with the example from the help text, i.e.
            Player 0: 100 points, competent
            Player 1: 80 points, inco
            Player 2: 40 points, competent
            Player 3: 30 points, competent
            Player 4: 20 points, inco
            Player 5: 10 points, competent
        """

        n = 10
        p = some_players(n)
        game = MockGame().having_assassins(p)
        plugin = ScoringPlugin()
        idents = [name + " identifier" for name in p]

        # assume initial competency of 1 day, skip to day 2 to make everyone inco
        initial_competency = 1
        game.new_datetime(2 * 24 * 60)

        # let players 0, 2, 3, 5 make kills for competency
        game.assassin(p[0]).kills(p[6])
        game.assassin(p[2]).kills(p[7])
        game.assassin(p[3]).kills(p[8])
        game.assassin(p[5]).kills(p[9])

        # set points using bonuses (which will be multiplied by 10)
        formula = "10 * b"
        bonuses = {
            idents[0]: 10,
            idents[1]: 8,
            idents[2]: 4,
            idents[3]: 3,
            idents[4]: 2,
            idents[5]: 1,
        }

        score_manager = self.get_manager(game, formula=formula, bonuses=bonuses)

        # verify scores
        for ident, bonus in bonuses.items():
            assert score_manager._score(ident) == bonus * 10

        competency_manager = get_competency_manager(game, initial_competency_period=initial_competency)

        def get_standings(max_duellists: int = 6,
                          allow_inco: bool = False,
                          pts_req_type: str = "lowest_qualifier",
                          pct_pts_req: float = 50,
                          soft_force: bool = True,
                          ):
            plugin.answer_set_duel_conditions({
                plugin.html_ids["Max Duellists"]: max_duellists,
                plugin.html_ids["Allow Inco Duellists?"]: allow_inco,
                plugin.html_ids["Points Requirement Type"]: pts_req_type,
                plugin.html_ids["% Points Requirement"]: pct_pts_req,
                plugin.html_ids["Soft-force Duel?"]: soft_force
            })
            return plugin.get_standings(
                live_assassins=game.get_remaining_player_models(),
                score_manager=score_manager,
                competency_manager=competency_manager,
                openseason_end=game.new_datetime(1)
            )

        """Requirements as per the main rules
        First two non-inco players 0 & 2 qualify.
        Player 3 satisfies points req because has >=50% of player 2's score.
        Everyone else is either inco or has < 50% of player 3's score.
        """
        duellists, excluded_incos, others = get_standings(6, False, "lowest_qualifier", 50, True)
        assert tuple(a.identifier for a in duellists) == (idents[0], idents[2], idents[3])
        assert tuple(a.identifier for a in excluded_incos) == (idents[1], idents[4])
        assert tuple(a.identifier for a in others) == (idents[5],)

        """As above but without soft-forcing.
        Only the inco player 1 satisfies the points requirement so player 1 wins outright."""
        duellists, excluded_incos, others = get_standings(6, False, "lowest_qualifier", 50, False)
        assert tuple(a.identifier for a in duellists) == (idents[0],)
        assert tuple(a.identifier for a in excluded_incos) == (idents[1],)
        assert tuple(a.identifier for a in others) == tuple(idents[2:6])

        """As above but with a 30% points requirement.
        Now everyone satisfies it."""
        duellists, excluded_incos, others = get_standings(6, False, "lowest_qualifier", 30, False)
        assert tuple(a.identifier for a in duellists) == (idents[0], idents[2], idents[3], idents[5])
        assert tuple(a.identifier for a in excluded_incos) == (idents[1], idents[4])
        assert len(others) == 0

        """As above but with a 35% points requirement.
        Only player 5 fails it."""
        duellists, excluded_incos, others = get_standings(6, False, "lowest_qualifier", 35, False)
        assert tuple(a.identifier for a in duellists) == (idents[0], idents[2], idents[3])
        assert tuple(a.identifier for a in excluded_incos) == (idents[1], idents[4])
        assert tuple(a.identifier for a in others) == (idents[5],)

        """Requirements as per the main rules but allowing incos.
        Everyone qualifies."""
        duellists, excluded_incos, others = get_standings(6, True, "lowest_qualifier", 35, True)
        assert tuple(a.identifier for a in duellists) == tuple(idents[0:6])
        assert len(excluded_incos) == 0
        assert len(others) == 0

        """No points requirement and max 5 duellists, no incos
        Only 4 non-inco players so these all qualify"""
        duellists, excluded_incos, others = get_standings(5, False, "none")
        assert tuple(a.identifier for a in duellists) == (idents[0], idents[2], idents[3], idents[5])
        assert tuple(a.identifier for a in excluded_incos) == (idents[1], idents[4])
        assert len(others) == 0

        """No points requirement and max 3 duellists, no incos.
        Now player 5 doesn't qualify, and the reasoning for player 4 is different."""
        duellists, excluded_incos, others = get_standings(3, False, "none")
        assert tuple(a.identifier for a in duellists) == (idents[0], idents[2], idents[3],)
        assert tuple(a.identifier for a in excluded_incos) == (idents[1],)
        assert tuple(a.identifier for a in others) == (idents[4], idents[5],)

        """Mich 2026 requirements: max 5 duellists, no incos, 50% of highest scoring, no forcing
        Only player 1 has enough points to qualify after the top player, but is inco.
        """
        duellists, excluded_incos, others = get_standings(5, False, "highest_qualifier", 50, False)
        assert tuple(a.identifier for a in duellists) == (idents[0],)
        assert tuple(a.identifier for a in excluded_incos) == (idents[1],)
        assert tuple(a.identifier for a in others) == tuple(idents[2:6])

        """As above but with a 30% points requirement
        Now players 2 and 3 do have enough points, but players 4 and 5 still fail it."""
        duellists, excluded_incos, others = get_standings(5, False, "highest_qualifier", 30, False)
        assert tuple(a.identifier for a in duellists) == (idents[0], idents[2], idents[3])
        assert tuple(a.identifier for a in excluded_incos) == (idents[1],)
        assert tuple(a.identifier for a in others) == tuple(idents[4:6])

        """Mich 2026 requirements except with soft forcing.
        Player 2 now qualifies but all subsequent players are still ineligible"""
        duellists, excluded_incos, others = get_standings(5, False, "highest_qualifier", 50, True)
        assert tuple(a.identifier for a in duellists) == (idents[0], idents[2],)
        assert tuple(a.identifier for a in excluded_incos) == (idents[1],)
        assert tuple(a.identifier for a in others) == tuple(idents[3:6])
