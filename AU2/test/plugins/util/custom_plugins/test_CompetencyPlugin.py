import pytest

from AU2.plugins.util.CompetencyManager import CompetencyManager
from AU2.test.test_utils import MockGame, some_players


class TestCompetencyPlugin:

    def get_manager(self, mockGame) -> CompetencyManager:
        m = CompetencyManager(game_start=mockGame.new_datetime())
        m.activated = True
        return m

    def test_competency_manager_simple(self):
        p = some_players(200)
        game = MockGame().having_assassins(p)
        manager = self.get_manager(game)
