from typing import List

from AU2.html_components.HTMLComponent import HTMLComponent
from AU2.html_components.SimpleComponents.SelectorList import SelectorList
from AU2.html_components.SimpleComponents.HiddenJSON import HiddenJSON
from AU2.plugins.CorePlugin import PLUGINS, CorePlugin
from AU2.test.test_utils import MockGame, some_players, plugin_test


def evaluate_components(components: List[HTMLComponent]) -> dict:
    out = {}
    for c in components:
        if isinstance(c, SelectorList):
            val = [t[1] if isinstance(t, tuple) else t for t in c.defaults]
            out[c.identifier] = val
        elif isinstance(c, HiddenJSON):
            out[c.identifier] = c.default
    return out


class TestIncorrectPseudonymFormatter:
    @plugin_test
    def test_simple(self):
        p = some_players(1)
        game = MockGame().having_assassins(p)
        p0 = game.assassin_model(p[0])._secret_id
        event = game.assassin(p[0]).is_involved_in_event(headline=f"[{p0}] does something.")\
            .with_report(p[0], 0, f"I am [{p0}]! I did something!")
        core_plugin: CorePlugin = PLUGINS["CorePlugin"]
        components = core_plugin.ask_generate_pages()
        html_response = evaluate_components(components)
        # now test fixing of headline and reports
        core_plugin.answer_generate_pages(html_response, True)
        e = event.model()
        assert e.headline == f"[P{p0}] does something."
        assert any(r[2] == f"I am [P{p0}]! I did something!" for r in e.reports)

    @plugin_test
    def test_underscores(self):
        p = some_players(1)
        game = MockGame().having_assassins(p)
        p0 = game.assassin_model(p[0])._secret_id
        event = game.assassin(p[0]).is_involved_in_event(headline=f"text_with_underscores [{p0}]_ text") \
            .with_report(p[0], 0, f" text_ _[P{p0}] text_with_underscores")
        core_plugin: CorePlugin = PLUGINS["CorePlugin"]
        components = core_plugin.ask_generate_pages()
        html_response = evaluate_components(components)
        # now test fixing of headline and reports
        core_plugin.answer_generate_pages(html_response, True)
        e = event.model()
        assert e.headline == f"text_with_underscores [P{p0}]_ text"
        assert any(r[2] == f" text_ _[P{p0}] text_with_underscores" for r in e.reports)
