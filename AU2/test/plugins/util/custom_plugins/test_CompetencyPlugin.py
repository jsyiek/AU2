import datetime

import pytest

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.plugins.util.CompetencyManager import CompetencyManager
from AU2.test.test_utils import MockGame, some_players, plugin_test


class TestCompetencyPlugin:

    def get_manager(self, mockGame) -> CompetencyManager:
        m = CompetencyManager(game_start=mockGame.new_datetime())
        m.activated = True
        m.initial_competency_period = datetime.timedelta(days=7)
        for e in EVENTS_DATABASE.events.values():
            m.add_event(e)
        return m

    @plugin_test
    def test_competency_manager_simple(self):
        p = some_players(200)
        game = MockGame().having_assassins(p)

        for i in range(50):
            game.assassin(p[i]).kills(p[i+50])

        manager = self.get_manager(game)
        query_date = manager.game_start + datetime.timedelta(days=7, seconds=30)

        incos = manager.get_incos_at(query_date)

        for i in range(50):
            assert ASSASSINS_DATABASE.get(p[i]+" identifier") not in incos

        for i in range(100):
            assert ASSASSINS_DATABASE.get(p[i+100]+" identifier") in incos
