import random

from math import isclose
from typing import Dict

from AU2.plugins.custom_plugins.MayWeekUtilitiesPlugin import MayWeekUtilitiesPlugin
from AU2.test.test_utils import plugin_test, some_players, MockGame


expected_scoring_params = [
    "starting_score_casual", "starting_score_full", "death_penalty_pct", "death_penalty_fixed", "kill_bonus_pct",
    "kill_bonus_fixed", "team_bonus_pct", "team_bonus_fixed", "multiplier_bonus_pct", "multiplier_bonus_fixed"
]


class TestMayWeekUtilitiesPlugin:
    def set_random_scoring_parameters(self) -> Dict[str, int]:
        """Helper function that sets random scoring parameters"""
        plugin = MayWeekUtilitiesPlugin()
        param_values = {
            # values 1 to 100 are valid for all the scoring parameters
            param.name: random.randint(1, 100) for param in plugin.scoring_parameters
        }

        # 'magnify' starting scores to reduce likelihood of stupidly large fixed bonus/penalty values
        param_values["starting_score_casual"] *= 10
        param_values["starting_score_full"] *= 10

        # set scoring parameters
        plugin.answer_set_scoring_params({
            plugin.html_ids[name]: value for name, value in param_values.items()
        })

        return param_values

    @plugin_test
    def test_set_scoring_params(self):
        plugin = MayWeekUtilitiesPlugin()

        param_values = self.set_random_scoring_parameters()

        # verify that params are set correctly
        for param_name in expected_scoring_params:
            assert plugin.gsdb_get(param_name) == param_values[param_name]

    @plugin_test
    def test_calculate_scores_no_gimmicks(self):
        """Tests that scores are calculated correctly when all gimmicks are disabled"""
        plugin = MayWeekUtilitiesPlugin()
        plugin.answer_set_gimmicks({plugin.html_ids["Gimmicks"]: []})
        param_values = self.set_random_scoring_parameters()

        d = param_values["death_penalty_pct"] / 100
        D = param_values["death_penalty_fixed"]
        b = param_values["kill_bonus_pct"] / 100
        B = param_values["kill_bonus_fixed"]
        Sc = param_values["starting_score_casual"]
        Sf = param_values["starting_score_full"]

        p = some_players(50)
        game = MockGame().having_assassins(p)

        game.assassin(p[0]).with_accomplices(*p[:20]).are_city_watch()

        # check that initial scores are correct
        scores, _ = plugin.calculate_scores()
        for name in p[:20]:
            assert scores[name + " identifier"] == Sc
        for name in p[20:]:
            assert scores[name + " identifier"] == Sf

        # test kills
        game.assassin(p[20]).kills(p[31])
        game.assassin(p[21]).kills(p[0])
        game.assassin(p[22]).kills(p[32], p[33])
        game.assassin(p[23]).kills(p[1], p[2])
        game.assassin(p[24]).kills(p[3], p[34])

        # for testing that multipliers, teams ignored when these are disabled
        e = game.assassin(p[25]).with_accomplices(p[40]).is_involved_in_event().model()
        plugin.eps_set(e, "Multiplier Transfers", [(None, p[25] + " identifier")])
        plugin.eps_set(e, "Team Changes", [(p[25] + " identifier", 1), (p[40] + " identifier", 1)])

        plugin.eps_set(
            game.assassin(p[25]).kills(p[35]).model(),
            "Kills as Team",
            [(p[25] + " identifier", p[35] + " identifier")]
        )

        # test BS points
        bs_points = {
            p[i] + " identifier": random.randint(1, 10) for i in (26, 36, 41)
        }
        plugin.eps_set(
            game.assassin(p[26]).with_accomplices(p[36], p[41]).is_involved_in_event().model(),
            "BS Points",
            bs_points
        )
        game.new_datetime()
        game.assassin(p[26]).kills(p[36])


        scores, perm_scores = plugin.calculate_scores()

        # since investment is disabled, permanent scores should all be 0
        for name in p:
            assert perm_scores[name + " identifier"] == 0

        # note: use isclose to test float values because we can get small rounding errors
        # casual victims
        for name in p[0:4]:
            assert isclose(scores[name + " identifier"], max(0, Sc - D - d*Sc))
        # full player victims
        for name in p[31:36]:
            assert isclose(scores[name + " identifier"], max(0, Sf - D - d*Sf))
        # full player killers
        assert isclose(scores[p[20] + " identifier"], Sf + B + b * Sf)  # killed a full player
        assert isclose(scores[p[21] + " identifier"], Sf + B + b * Sc)  # killed a casual player
        assert isclose(scores[p[22] + " identifier"], Sf + 2*(B + b * Sf))  # killed two full players
        assert isclose(scores[p[23] + " identifier"], Sf + 2*(B + b * Sc))  # killed two casual players
        assert isclose(scores[p[24] + " identifier"], Sf + B + b * Sf + B + b * Sc)  # killed one full one casual player
        assert isclose(scores[p[25] + " identifier"], Sf + B + b * Sf)  # killed a full player (with ignored team kill + multiplier)

        assert scores[p[40] + " identifier"] == Sf  # player on the same team as a team kill

        # scores involving BS points
        assert isclose(scores[p[26] + " identifier"], (
                Sf + bs_points[p[26] + " identifier"] + B + b * (
                    Sf + bs_points[p[36] + " identifier"]
                )
        ))  # has BS points + killed a player with BS points
        assert isclose(scores[p[36] + " identifier"], max(0, (1 - d) * (Sf + bs_points[p[36] + " identifier"]) - D))  # victim with BS points
        assert isclose(scores[p[41] + " identifier"], Sf + bs_points[p[41] + " identifier"])  # no kills

    @plugin_test
    def test_investment_first(self):
        """
        Tests the permanent/temporary scores gimmick ONLY, with investment occurring first.
        """
        plugin = MayWeekUtilitiesPlugin()
        plugin.answer_set_gimmicks({plugin.html_ids["Gimmicks"]: ["investment"]})
        param_values = self.set_random_scoring_parameters()

        b = param_values["kill_bonus_pct"] / 100
        B = param_values["kill_bonus_fixed"]
        Sf = param_values["starting_score_full"]

        invest_pct = random.randint(1, 100)
        plugin.answer_config_perm_points({
            plugin.html_ids["Investment %"]: invest_pct,
            plugin.html_ids["Invest first?"]: True,
            plugin.html_ids["Deplete Permanent Points?"]: True,
            plugin.html_ids["Perm Points Floor"]: None,
            plugin.html_ids["Visible Points"]: [],
        })
        invest_prop = invest_pct / 100
        keep_prop = 1 - invest_prop  # proportion of temporary points NOT invested

        p = some_players(50)
        game = MockGame().having_assassins(p)
        # ensure that the starting hour is 1pm so that we can test the 'same day' condition properly
        game.date = game.date.replace(hour=13)

        # give a player 0 BS points
        bs_points = random.randint(1, 10)
        plugin.eps_set(
            game.assassin(p[0]).is_involved_in_event().model(),
            "BS Points",
            {p[0] + " identifier": bs_points}
        )
        game.new_datetime()

        # some kills
        game.assassin(p[0]).kills(p[10])
        plugin.eps_set(
            game.assassin(p[1]).kills(p[11]).model(),
            "BS Points",
            {p[1] + " identifier": bs_points}
        )

        temp_scores, perm_scores = plugin.calculate_scores()
        # player 0's first kill of the day occurs after getting BS points, so invests some of it
        assert isclose(perm_scores[p[0] + " identifier"], invest_prop * (Sf + bs_points))
        assert isclose(temp_scores[p[0] + " identifier"], keep_prop * (Sf + bs_points) + B + b * Sf)
        # on the other hand, player 1 gains the BS points during the kill so they aren't invested
        assert isclose(perm_scores[p[1] + " identifier"], invest_prop * Sf)
        assert isclose(temp_scores[p[1] + " identifier"], keep_prop * Sf + B + b * Sf + bs_points)

        # no other players should have any permanent points at this stage either
        for name in p[2:]:
            assert perm_scores[name + " identifier"] == 0

        # now, move later in same day and add more kills for the same players. They shouldn't invest any more!
        game.new_datetime(minutes=4*60)
        game.assassin(p[0]).kills(p[12])  # new kill
        game.assassin(p[1]).kills(p[11])  # old kill
        game.assassin(p[2]).kills(p[10])  # new kill for player 2 but old victim

        temp_scores2, perm_scores2 = plugin.calculate_scores()

        # permanent scores for players 0, 1 shouldn't change
        for name in p[:2]:
            assert perm_scores2[name + " identifier"] == perm_scores[name + " identifier"]
        # but player 2 should invest here
        assert isclose(perm_scores2[p[2] + " identifier"], invest_prop * Sf)
        assert isclose(temp_scores2[p[2] + " identifier"], keep_prop * Sf + B + b * temp_scores[p[10] + " identifier"])
        # and all the killer's temp scores should change
        assert isclose(temp_scores2[p[0] + " identifier"],
                       temp_scores[p[0] + " identifier"] + B + b * Sf)
        assert isclose(temp_scores2[p[1] + " identifier"],
                       temp_scores[p[1] + " identifier"] + B + b * temp_scores[p[11] + " identifier"])

        # now move to the next day (but less than 24 hrs from the original kills!)
        game.new_datetime(minutes=16*60)
        game.assassin(p[0]).kills(p[12])  # old kill
        game.assassin(p[1]).kills(p[10])  # new kill
        game.assassin(p[2]).kills(p[11], p[13])  # two new kills: only triggers one investment...

        temp_scores3, perm_scores3 = plugin.calculate_scores()
        # player 0 shouldn't have invested anything, since they killed someone they already had
        assert perm_scores3[p[0] + " identifier"] == perm_scores2[p[0] + " identifier"]
        # but both players 1 and 2 should have invested again
        assert isclose(perm_scores3[p[1] + " identifier"],
                       perm_scores2[p[1] + " identifier"] + invest_prop * temp_scores2[p[1] + " identifier"])
        assert isclose(perm_scores3[p[2] + " identifier"],
                       perm_scores2[p[2] + " identifier"] + invest_prop * temp_scores2[p[2] + " identifier"])

        # also check that temp scores updated correctly
        assert isclose(temp_scores3[p[0] + " identifier"],
                       temp_scores2[p[0] + " identifier"] + B + b * temp_scores2[p[12] + " identifier"])
        assert isclose(temp_scores3[p[1] + " identifier"],
                       keep_prop * temp_scores2[p[1] + " identifier"] + B + b * temp_scores2[p[10] + " identifier"])
        assert isclose(temp_scores3[p[2] + " identifier"],
                       keep_prop * temp_scores2[p[2] + " identifier"]
                       + B + b * temp_scores2[p[11] + " identifier"]
                       + B + b * temp_scores2[p[13] + " identifier"])

    @plugin_test
    def test_betting_gold(self):
        """Unit test to check that permenant points can be depleted using -ve BS points"""
        plugin = MayWeekUtilitiesPlugin()
        plugin.answer_set_gimmicks({plugin.html_ids["Gimmicks"]: ["investment"]})
        param_values = self.set_random_scoring_parameters()

        # set these params deterministically to guarantee that we deplete permanent points
        param_values["kill_bonus_pct"] = 0
        param_values["kill_bonus_fixed"] = 0
        param_values["starting_score_full"] = 10
        plugin.answer_set_scoring_params({
            plugin.html_ids[name]: value for name, value in param_values.items()
        })
        invest_pct = 50
        plugin.answer_config_perm_points({
            plugin.html_ids["Investment %"]: invest_pct,
            plugin.html_ids["Invest first?"]: True,
            plugin.html_ids["Deplete Permanent Points?"]: True,
            plugin.html_ids["Perm Points Floor"]: None,
            plugin.html_ids["Visible Points"]: [],
        })
        invest_prop = invest_pct / 100

        p = some_players(2)
        game = MockGame().having_assassins(p)

        # a kill to get some points invested
        game.assassin(p[0]).kills(p[1])
        temp_scores, perm_scores = plugin.calculate_scores()
        assert perm_scores[p[0] + " identifier"] == 5
        assert temp_scores[p[0] + " identifier"] == 5  # kill bonuses are set to 0 for this unit test

        # negative BS points to deplete permanent points
        game.new_datetime()
        plugin.eps_set(
            game.assassin(p[0]).is_involved_in_event().model(),
            "BS Points",
            {p[0] + " identifier": -8}
        )
        temp_scores2, perm_scores2 = plugin.calculate_scores()
        assert perm_scores2[p[0] + " identifier"] == 2
        assert temp_scores2[p[0] + " identifier"] == 0

        # check that perm points can go negative when no floor is set
        game.new_datetime()
        plugin.eps_set(
            game.assassin(p[0]).is_involved_in_event().model(),
            "BS Points",
            {p[0] + " identifier": -8}
        )
        temp_scores3, perm_scores3 = plugin.calculate_scores()
        assert perm_scores3[p[0] + " identifier"] == -6
        assert temp_scores3[p[0] + " identifier"] == 0
