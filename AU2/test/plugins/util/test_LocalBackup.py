from AU2.plugins.CorePlugin import CorePlugin
from AU2.test.test_utils import MockGame, some_players, Database, plugin_test


class TestLocalBackupPlugin:

    @plugin_test
    def test_nuke_database(self):
        """
        Confirms the database is nuked when requested
        """

        p = some_players(200)
        game = MockGame().having_assassins(p)                                           \
                         .assassin(p[0]).with_accomplices(p[1], p[2], p[3]).kills(p[4]).then() \
                         .assassin(p[5]).kills(p[6]).then()                                    \
                         .assassin(p[7]).kills(p[8]).then()                                    \
                         .assassin(p[9]).kills(p[10])

        plugin = CorePlugin()

        Database.has_assassin(p[0])                         \
                .having.identifier(p[0] + " identifier")   \
                .having.college(p[0] + " college")

        Database.has_events(4)

        plugin.answer_reset_database({
            plugin.identifier + "_DigitsChallenge_HiddenTextbox": "12345",
            plugin.identifier + "_DigitsChallenge_NamedSmallTextbox": "12345",
        })

        for player in p:
            Database.doesnt_have_assassin(player)

        Database.has_no_events()
