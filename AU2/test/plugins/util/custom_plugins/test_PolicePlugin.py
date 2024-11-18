import datetime

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import Event
from AU2.plugins.custom_plugins.PolicePlugin import PolicePlugin
from AU2.test.test_utils import MockGame, some_players, plugin_test, dummy_event


class TestPolicePlugin:

    @plugin_test
    def test_resurrect_as_police(self):
        """
        Tests that Assassin -> Resurrect as Police
        """
        k = 50
        n = 4*k
        p = some_players(n)
        game = MockGame().having_assassins(p)
        plugin = PolicePlugin()

        # add some regular deaths
        for i in range(k):
            game.assassin(p[i]).kills(p[i + k])
        # add some police deaths
        for i in range(2*k, 3*k):
            game.assassin(p[i + k]).is_police()
            game.assassin(p[i]).kills(p[i + k])

        # hide some assassins
        game.assassin(p[k-1]).with_accomplices(p[2*k-1], p[3*k-1], p[4*k-1]).are_hidden()

        # check that the list of players that can be resurrected is correct
        # (only the dead non-police, non-hidden assassins should be shown!)
        assert set(plugin.gather_dead_non_police()) == {p[i] + " identifier" for i in range(k, 2*k-1)}

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
        plugin.answer_resurrect_as_police({plugin.html_ids["Assassin"]: p[k] + " identifier",
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
        assert new_assassin.is_police
        for key, val in to_copy.items():
            assert getattr(new_assassin, key) == val
        assert new_assassin.pseudonyms == [new_pseudonym]
        assert new_assassin.pseudonym_datetimes == {}
        # check the list of resurrectable assassins is correct after resurrection
        assert old_assassin.hidden
        assert set(plugin.gather_dead_non_police()) == {p[i] + " identifier" for i in range(k+1, 2 * k - 1)}
