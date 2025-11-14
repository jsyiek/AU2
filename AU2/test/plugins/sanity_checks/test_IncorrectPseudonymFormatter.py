from AU2.plugins.CorePlugin import CorePlugin
from AU2.test.test_utils import evaluate_components, MockGame, plugin_test, some_players


class TestIncorrectPseudonymFormatter:
    @plugin_test
    def test_simple(self):
        p = some_players(1)
        game = MockGame().having_assassins(p)
        p0 = game.assassin_model(p[0])._secret_id
        event = game.assassin(p[0]).is_involved_in_event(headline=f"[{p0}] does something.")\
            .with_report(p[0], 0, f"I am [{p0}]! I did something!")
        core_plugin = CorePlugin()
        components = core_plugin.ask_generate_pages()
        html_response = evaluate_components(components)
        # now test fixing of headline and reports
        core_plugin.answer_generate_pages(html_response, True)
        e = event.model()
        assert e.headline == f"[P{p0}] does something."
        assert event.check_report(f"I am [P{p0}]! I did something!")

    @plugin_test
    def test_underscores(self):
        p = some_players(1)
        game = MockGame().having_assassins(p)
        p0 = game.assassin_model(p[0])._secret_id
        event = game.assassin(p[0]).is_involved_in_event(headline=f"text_with_underscores [{p0}]_ text") \
            .with_report(p[0], 0, f" text_ _[P{p0}] text_with_underscores")
        core_plugin = CorePlugin()
        components = core_plugin.ask_generate_pages()
        html_response = evaluate_components(components)
        # now test fixing of headline and reports
        core_plugin.answer_generate_pages(html_response, True)
        e = event.model()
        assert e.headline == f"text_with_underscores [P{p0}]_ text"
        assert event.check_report(f" text_ _[P{p0}] text_with_underscores")
