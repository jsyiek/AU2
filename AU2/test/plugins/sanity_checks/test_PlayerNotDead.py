from AU2.plugins.CorePlugin import PLUGINS, CorePlugin
from AU2.test.test_utils import evaluate_components, MockGame, plugin_test, some_players


class TestPlayerNotDead:
    @plugin_test
    def test_simple(self):
        p = some_players(2)
        game = MockGame().having_assassins(p)
        n = [game.assassin(q).model(q)._secret_id for q in p]
        event = game.assassin(p[0]).kills(p[1], headline=f"[D{n[0]}] kills [D{n[1]}] ([N{n[1]}])!")\
            .with_report(p[1], 0, f"blah blah blah [N{n[0]}] blah blah")
        core_plugin: CorePlugin = PLUGINS["CorePlugin"]
        components = core_plugin.ask_generate_pages()
        html_response = evaluate_components(components)
        # now test fixing of headline and reports
        core_plugin.answer_generate_pages(html_response, True)
        e = event.model()
        assert e.headline == f"[P{n[0]}] kills [D{n[1]}] ([N{n[1]}])!"
        assert any(r[2] == f"blah blah blah [P{n[0]}] blah blah" for r in e.reports)
