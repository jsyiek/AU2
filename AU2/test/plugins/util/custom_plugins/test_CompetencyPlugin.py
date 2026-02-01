import datetime

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.plugins.custom_plugins.CompetencyPlugin import CompetencyPlugin
from AU2.plugins.util.CompetencyManager import CompetencyManager
from AU2.test.test_utils import MockGame, some_players, plugin_test, dummy_event


class TestCompetencyPlugin:

    def get_manager(self, mockGame, auto_competency=False, initial_competency_period=7) -> CompetencyManager:
        m = CompetencyManager(game_start=mockGame.game_start)
        m.activated = True
        m.auto_competency = auto_competency
        m.initial_competency_period = datetime.timedelta(days=initial_competency_period)
        for e in EVENTS_DATABASE.events.values():
            m.add_event(e)
        return m

    @plugin_test
    def test_competency_manager_simple(self):
        """
        50 players kill 50 others
        Only those initial 50 should be competent
        And no dead players should be competent
        """
        p = some_players(200)
        game = MockGame().having_assassins(p)

        for i in range(50):
            game.assassin(p[i]).kills(p[i + 50])

        manager = self.get_manager(game)
        query_date = manager.game_start + datetime.timedelta(days=7, seconds=30)

        incos = manager.get_incos_at(query_date)
        print(EVENTS_DATABASE.events.values())

        for i in range(50):
            assert ASSASSINS_DATABASE.get(p[i] + " identifier") not in incos

        for i in range(100):
            assert ASSASSINS_DATABASE.get(p[i + 100] + " identifier") in incos

        # OK for dead players to be inco - some games may support non-perma death
        assert len(incos) == 150

    @plugin_test
    def test_competency_manager_game_start(self):
        """
        All players should be competent at the game start.
        """
        p = some_players(200)
        game = MockGame().having_assassins(p)

        manager = self.get_manager(game)

        incos = manager.get_incos_at(manager.game_start)

        assert len(incos) == 0

    @plugin_test
    def test_competency_plugin_event_create(self):
        """
        Test that the competency plugin adds competency field to an event.
        """
        event = dummy_event()
        plugin = CompetencyPlugin()
        plugin.on_event_create(
            event,
            {plugin.html_ids["Competency"]: {"a1": 5, "a2": 7}}
        )

        assert event.pluginState.get("CompetencyPlugin", {}).get("competency", {}).get("a1") == 5
        assert event.pluginState.get("CompetencyPlugin", {}).get("competency", {}).get("a2") == 7

    @plugin_test
    def test_competency_plugin_event_update(self):
        """
        Test that the competency plugin adds competency field to an event.
        """
        event = dummy_event()
        plugin = CompetencyPlugin()
        event.pluginState = {plugin.html_ids["Competency"]: {"a1": 3}, "foobar": "foobar"}
        plugin.on_event_update(
            event,
            {plugin.html_ids["Competency"]: {"a1": 5, "a2": 7}}
        )

        assert event.pluginState.get("CompetencyPlugin", {}).get("competency", {}).get("a1") == 5
        assert event.pluginState.get("CompetencyPlugin", {}).get("competency", {}).get("a2") == 7
        assert event.pluginState.get("foobar") == "foobar"

    @plugin_test
    def test_kills_auto_competency(self):
        """
        Test that kills grant auto competency properly.
        5 players should have competency after this (i.e. the remaining 15 are inco)
        """
        p = some_players(20)
        game = MockGame().having_assassins(p)

        for i in range(5):
            game.assassin(p[i]).kills(p[i + 5])

        manager = self.get_manager(game, auto_competency=True, initial_competency_period=0)
        query_date = manager.game_start + datetime.timedelta(days=1, seconds=30)

        incos = manager.get_incos_at(query_date)
        print(EVENTS_DATABASE.events.values())

        for i in range(5):
            assert ASSASSINS_DATABASE.get(p[i] + " identifier") not in incos

        for i in range(10):
            assert ASSASSINS_DATABASE.get(p[i + 10] + " identifier") in incos

        assert len(incos) == 15

    @plugin_test
    def test_attempts_auto_competency(self):
        """
        Test that attempts grant auto competency properly, especially with multiple.
        Checks whether a player with 0 or 1 attempt is inco, and one with 2, 3, or 2 spread over different events is not
        """
        # TODO refactor this to use Alexei's MockGame.add_attempts() once that is merged
        p = some_players(5)
        game = (MockGame().having_assassins(p)
                .add_attempts(p[1])
                .add_attempts(p[2], p[2])
                .add_attempts(p[3], p[3], p[3])
                .add_attempts(p[4])
                .add_attempts(p[4]))

        manager = self.get_manager(game, auto_competency=True, initial_competency_period=0)
        query_date = manager.game_start + datetime.timedelta(days=1, seconds=30)

        incos = manager.get_incos_at(query_date)

        for i in range(3):
            assert ASSASSINS_DATABASE.get(p[i+2] + " identifier") not in incos

        for i in range(2):
            assert ASSASSINS_DATABASE.get(p[i] + " identifier") in incos

        assert len(incos) == 2

    @plugin_test
    def test_gigabolt(self):
        """
        Test that only full players with no kills and no attempts will be eliminated.
        """
        p = some_players(20)
        game = (MockGame().having_assassins(p)
                .assassin(p[19]).is_city_watch()
                .assassin(p[18]).is_city_watch()
                .assassin(p[0]).kills(p[1])
                .assassin(p[2]).kills(p[3])
                .assassin(p[4]).kills(p[5])
                .assassin(p[6]).kills(p[7])
                .add_attempts(p[15])
                .add_attempts(p[16], p[16], p[16]))

        plugin = CompetencyPlugin()

        plugin.gigabolt_answer(
            htmlResponse={
                plugin.html_ids["Gigabolt"]: next((c.defaults for c in plugin.gigabolt_ask() if c.identifier == plugin.html_ids["Gigabolt"])),
                plugin.html_ids["Umpire"]: p[19],
                plugin.html_ids["Datetime"]: game.new_datetime(),
                plugin.html_ids["Headline"]: "",
            }
        )

        game.refresh_deaths_from_db()

        assert len(game.get_remaining_players()) == 8

    @plugin_test
    def test_list_of_inco_corpses(self, auto_competency: bool = True):
        """
        Tests that the list of corpses for the inco page is computed correctly.
        """
        p = some_players(250)
        game = MockGame().having_assassins(p)

        # first players 51-100 die while not inco
        for i, j in zip(range(50), range(51, 100)):
            game.assassin(p[i]).kills(p[j])

        # fast forwards 15 days so all players are inco
        game.new_datetime(minutes=60 * 24 * 15)

        # players 101-150 die while inco, and players 1-50 gain competency
        for i, j in zip(range(1, 50), range(101, 150)):
            game.assassin(p[i]).kills(p[j])

        # fast forwards 1 day
        game.new_datetime(minutes=60 * 24)

        # players 201-250 become competent through attempts
        for i in range(201, 250):
            if auto_competency:
                game.add_attempts(p[i], p[i])  # double attempt => competency
            else:
                # manual competency
                game.assassin(p[i]).is_involved_in_event(
                    pluginState={"CompetencyPlugin": {"competency": {p[i] + " identifier": 7}}}
                )

        # fast forwards 1 day
        game.new_datetime(minutes=60 * 24)

        # players 201-250 die while competent from attempts after previously being inco
        for i, j in zip(range(1, 50), range(201, 250)):
            game.assassin(p[i]).kills(p[j])

        # now check the inco corpses
        manager = self.get_manager(game, auto_competency=auto_competency)
        inco_corpses = manager.inco_corpses

        # neither the live, competent players,
        # nor the first set of players who died while competent,
        # should be inco corpses
        for i in range(100):
            assert ASSASSINS_DATABASE.get(p[i] + " identifier") not in inco_corpses

        # the players who died while inco should be inco corpses
        for i in range(101, 150):
            assert ASSASSINS_DATABASE.get(p[i] + " identifier") in inco_corpses

        # neither the live inco players,
        # nor the second set of players who died while competent,
        # should be inco corpses
        for i in range(151, 250):
            assert ASSASSINS_DATABASE.get(p[i] + " identifier") not in inco_corpses

    def test_inco_corpses_manual_competency(self):
        self.test_list_of_inco_corpses(auto_competency=False)
