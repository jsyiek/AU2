from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.plugins.custom_plugins.CityWatchPlugin import CityWatchPlugin
from AU2.plugins.util.CityWatchRankManager import CityWatchRankManager
from AU2.test.test_utils import MockGame, some_players, plugin_test


class TestCityWatchPlugin:
    def get_manager(self, auto_ranking=True, city_watch_kill_ranking=False) -> CityWatchRankManager:
        m = CityWatchRankManager(auto_ranking=auto_ranking, city_watch_kill_ranking=city_watch_kill_ranking)
        for e in EVENTS_DATABASE.events.values():
            m.add_event(e)
        return m

    @plugin_test
    def test_resurrect_as_city_watch(self):
        """
        Tests that Assassin -> Resurrect as City Watch
        """
        k = 50
        n = 4*k
        p = some_players(n)
        game = MockGame().having_assassins(p)
        plugin = CityWatchPlugin()

        # add some regular deaths
        for i in range(k):
            game.assassin(p[i]).kills(p[i + k])
        # add some city watch deaths
        for i in range(2*k, 3*k):
            game.assassin(p[i + k]).is_city_watch()
            game.assassin(p[i]).kills(p[i + k])

        # hide some assassins
        game.assassin(p[k-1]).with_accomplices(p[2*k-1], p[3*k-1], p[4*k-1]).are_hidden()

        # check that the list of players that can be resurrected is correct
        # (only the dead, non-hidden full players should be shown!)
        assert set(plugin.gather_dead_full_players()) == {p[i] + " identifier" for i in range(k, 2 * k - 1)}

        # check that players get resurrected correctly
        ##############################################
        new_pseudonym = "New Pseudonym"
        old_assassin = ASSASSINS_DATABASE.get(p[k] + " identifier")
        old_idents = set(ASSASSINS_DATABASE.get_identifiers(include_hidden=lambda _: True))
        # the way identifiers are generated in test mode messes with cloning
        # this is kind of hacky but at least lets us verify that Assassin.__post_init__ gets called
        old_assassin.real_name = old_assassin.real_name + " The Great"
        to_copy = {
            "real_name" : old_assassin.real_name,
            "email" : old_assassin.email,
            "college" : old_assassin.college,
            "address" : old_assassin.address,
            "water_status": old_assassin.water_status,
            "notes": old_assassin.notes,
            "pronouns": old_assassin.pronouns
        }
        plugin.answer_resurrect_as_city_watch({plugin.html_ids["Assassin"]: p[k] + " identifier",
                                               plugin.html_ids["Pseudonym"]: new_pseudonym})
        # implicitly this verifies that the clone has a unique identifier
        new_assassins = ASSASSINS_DATABASE.get_filtered(include=lambda a: a.identifier not in old_idents)
        assert len(new_assassins) == 1
        new_assassin = new_assassins[0]
        # check database integrity
        assert ASSASSINS_DATABASE.get(new_assassin.identifier) == new_assassin
        assert ASSASSINS_DATABASE.get(p[k] + " identifier") != new_assassin
        # check new assassin has correct attributes
        assert not new_assassin.hidden
        assert new_assassin.is_city_watch
        for key, val in to_copy.items():
            assert getattr(new_assassin, key) == val
        assert new_assassin.pseudonyms == [new_pseudonym]
        assert new_assassin.pseudonym_datetimes == {}
        # check the list of resurrectable assassins is correct after resurrection
        assert old_assassin.hidden
        assert set(plugin.gather_dead_full_players()) == {p[i] + " identifier" for i in range(k + 1, 2 * k - 1)}

    @plugin_test
    def test_can_handle_thunderbolt(self):
        """
        Have 20 players, players 0-9 city watch, rest full players.
        Then kill graph
        0 -> 10
        |--> 11

        Thunderbolt -> 12
            |--------> 1
        """
        p = some_players(20)
        game = MockGame().having_assassins(p)
        game.assassin(p[0]).with_accomplices(*p[1:10]).are_city_watch()

        game.assassin(p[0]).kills(p[10]).then()\
            .assassin(p[0]).kills(p[11]).then()\
            .assassin(p[12]).is_thunderbolted().then()\
            .assassin(p[1]).is_thunderbolted()

        manager = self.get_manager()

        # player 0 has two kills -> two rankups
        assert manager.get_relative_rank(p[0] + " identifier") == 2
        # other city watch have no kills
        for i in range(1, 10):
            assert manager.get_relative_rank(p[i] + " identifier") == 0
