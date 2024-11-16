import datetime

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.plugins.custom_plugins.CompetencyPlugin import CompetencyPlugin
from AU2.plugins.util.CompetencyManager import CompetencyManager
from AU2.plugins.util.DeathManager import DeathManager
from AU2.test.test_utils import MockGame, some_players, plugin_test, dummy_event


class TestCompetencyPlugin:

    def get_manager(self, mockGame, auto_competency=False, initial_competency_period=7) -> CompetencyManager:
        m = CompetencyManager(game_start=mockGame.new_datetime())
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
                .assassin(p[1]).is_involved_in_event(pluginState={"CompetencyPlugin": {"attempts": [p[1] + " identifier"]}})
                .assassin(p[2]).is_involved_in_event(
                    pluginState={"CompetencyPlugin": {"attempts": [p[2] + " identifier"] * 2}})
                .assassin(p[3]).is_involved_in_event(
                    pluginState={"CompetencyPlugin": {"attempts": [p[3] + " identifier"] * 3}})
                .assassin(p[4]).is_involved_in_event(
                    pluginState={"CompetencyPlugin": {"attempts": [p[4] + " identifier"]}})
                .assassin(p[4]).is_involved_in_event(
                    pluginState={"CompetencyPlugin": {"attempts": [p[4] + " identifier"]}}))

        manager = self.get_manager(game, auto_competency=True, initial_competency_period=0)
        query_date = manager.game_start + datetime.timedelta(days=1, seconds=30)

        incos = manager.get_incos_at(query_date)
        print(EVENTS_DATABASE.events.values())

        for i in range(3):
            assert ASSASSINS_DATABASE.get(p[i+2] + " identifier") not in incos

        for i in range(2):
            assert ASSASSINS_DATABASE.get(p[i] + " identifier") in incos

        assert len(incos) == 2

    @plugin_test
    def test_gigabolt(self):
        """
        Test that only non-police players with no kills and no attempts will be eliminated.
        The dangerous logic for gigabolt is in CompetencyPlugin.gigabolt_ask (i.e. the default selections),
        while this only tests gigabolt_answer directly. It is mostly just code copy-pasted from gigabolt_ask,
        and thus is not really a good test
        """
        p = some_players(20)
        game = (MockGame().having_assassins(p)
                .assassin(p[19]).is_police()
                .assassin(p[18]).is_police()
                .assassin(p[0]).kills(p[1])
                .assassin(p[2]).kills(p[3])
                .assassin(p[4]).kills(p[5])
                .assassin(p[6]).kills(p[7])
                .assassin(p[15]).is_involved_in_event(
            pluginState={"CompetencyPlugin": {"attempts": [p[15] + " identifier"]}})
                .assassin(p[16]).is_involved_in_event(
            pluginState={"CompetencyPlugin": {"attempts": [p[15] + " identifier"] * 3}}))
        # TODO refactor this to use Alexei's MockGame.add_attempts() once that is merged
        plugin = CompetencyPlugin()

        active_players = []
        death_manager = DeathManager()
        for e in list(EVENTS_DATABASE.events.values()):
            death_manager.add_event(e)
            for killer, _ in e.kills:
                active_players.append(killer)
            for player_id in e.pluginState.get("CompetencyPlugin", {}).get("attempts", []):
                active_players.append(player_id)
        active_players = set(active_players)

        plugin.gigabolt_answer(
            htmlResponse={
                plugin.html_ids["Gigabolt"]: ASSASSINS_DATABASE.get_identifiers(
                    include=lambda a: not (a.is_police or death_manager.is_dead(a) or a.identifier in active_players)),
                plugin.html_ids["Umpire"]: p[19],
                plugin.html_ids["Datetime"]: game.new_datetime(),
                plugin.html_ids["Headline"]: "",
            }
        )
        # Have to use a death manager, because the gigabolt kill events don't call MockGame.has_died
        death_manager = DeathManager()
        for e in list(EVENTS_DATABASE.events.values()):
            death_manager.add_event(e)
        live_players = [i for i in ASSASSINS_DATABASE.assassins.values() if not death_manager.is_dead(i)]
        assert len(live_players) == 8
