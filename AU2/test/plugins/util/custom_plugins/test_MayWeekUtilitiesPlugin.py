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
            # values 0 to 100 are valid for all the scoring parameters
            param.name: random.randint(0, 100) for param in plugin.scoring_parameters
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

        # casual victims
        for name in p[0:4]:
            assert scores[name + " identifier"] == max(0, Sc - D - d*Sc)
        # full player victims
        for name in p[31:36]:
            assert scores[name + " identifier"] == max(0, Sf - D - d*Sf)
        # full player killers
        # note: use isclose to test float values because we can get small rounding errors
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
