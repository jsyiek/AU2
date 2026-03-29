from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.plugins.util.DeathManager import DeathManager
from AU2.test.test_utils import MockGame, plugin_test, some_players

class TestDeathManager:
    def get_manager(self) -> DeathManager:
        m = DeathManager()
        for e in EVENTS_DATABASE.events.values():
            m.add_event(e)
        return m

    @plugin_test
    def test_can_handle_thunderbolt(self):
        """
        Test that DeathManager can deal with thunderbolt deaths
        """
        p = some_players(20)
        game = MockGame().having_assassins(p)

        # some kills
        for i in range(5):
            game.assassin(p[i]).kills(p[i + 5], manual_competency=None)
        # some thunderbolts
        game.assassin(p[10]).with_accomplices(*p[11:15]).are_thunderbolted()

        manager = self.get_manager()

        # check right players counted as dead
        for i in range(20):
            if i < 5 or i >= 15:
                assert not manager.is_dead(game.assassin_model(p[i]))
            else:
                assert manager.is_dead(game.assassin_model(p[i]))
