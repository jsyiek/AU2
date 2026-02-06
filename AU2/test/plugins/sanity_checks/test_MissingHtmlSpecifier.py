from AU2.plugins.CorePlugin import CorePlugin
from AU2.test.test_utils import evaluate_components, MockGame, plugin_test, some_players


class TestMissingHtmlSpecifier:
    @plugin_test
    def test_simple(self):
        p = some_players(3)
        game = MockGame().having_assassins(p)
        event = game.assassin(p[0]).with_accomplices(p[1], p[2])\
            .is_involved_in_event(headline="We <b>don't</b> need a specifier in the headline")\
            .with_report(p[0], 0, "But we <em>do</em> need it for reports!")\
            .with_report(p[1], 0, "<!--HTML--> Unless we <b>already</b> have a html specifier...")\
            .with_report(p[2], 0, "Or there is no HTML!")
        core_plugin = CorePlugin()
        components = core_plugin.ask_generate_pages()
        html_response = evaluate_components(components)
        # now test fixing of headline and reports
        core_plugin.answer_generate_pages(html_response, True)
        e = event.model()
        assert e.headline == "We <b>don't</b> need a specifier in the headline"
        assert event.check_report("<!--HTML-->But we <em>do</em> need it for reports!")
        assert event.check_report("<!--HTML--> Unless we <b>already</b> have a html specifier...")
        assert event.check_report("Or there is no HTML!")
