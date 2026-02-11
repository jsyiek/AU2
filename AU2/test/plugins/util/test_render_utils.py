from AU2.plugins.util.render_utils import adjust_brightness, render_headline_and_reports
from AU2.test.test_utils import MockGame, plugin_test, some_players


def dummy_color_fn(pseudonym, a, e, managers) -> str:
    return "#00FF00"


class TestRenderUtils:
    def test_adjust_brightness(self):
        assert adjust_brightness("#a7b231", 1).lower() == "#a7b231"
        assert adjust_brightness("#64091b", 0).lower() == "#000000"
        assert adjust_brightness("#c9d1c4", -10).lower() == "#000000"
        assert adjust_brightness("#a81245", 255).lower() == "#ffffff"
        assert adjust_brightness("#15a28b", 0.5).lower() == "#0a5145"
        assert adjust_brightness("#88bc0f", 1/3).lower() == "#2d3e05"

    @plugin_test
    def test_markdown(self):
        p = some_players(2)
        game = MockGame().having_assassins(p)

        game.assassin_model(p[0]).pseudonyms = ["Test pseudonym"]
        game.assassin_model(p[1]).pseudonyms = ["<i>Escaped HTML pseudonym</i>",
                                                "<!--HTML--><i>Unescaped HTML pseudonym</i>"]
        event = game.assassin(p[0]).with_accomplices(p[1]).is_involved_in_event(
            headline=f"Testing **markdown** in headlines and interaction with *{game.pcode(p[0])}*'s non-html pseudonym "
                     f"code, and the html pseudonym of ~~{game.pcode(p[1], 0)}~~ I mean {game.pcode(p[1], 1)}(also "
                     f"ensuring pseudonym codes aren't interpreted as hyperlinks)."
        ).with_report(p[0], 0, f"Testing **markdown** in reports and interaction with *{game.pcode(p[0])}*'s pseudonym code.")\
        .with_report(p[1], 0, f"Testing\nmultiline\n\nreports.")\
        .with_report(p[1], 1, "<!--HTML-->Testing that markdown is **ignored** in HTML-enabled reports.\n"
                              "Including:\n\n"
                              "Leaving newlines as-is.")
        headline, reports = render_headline_and_reports(event.model(), (), dummy_color_fn)
        assert headline == ("Testing <strong>markdown</strong> in headlines and interaction with "
                            "<em><b style=\"color:#00FF00\">Test pseudonym</b></em>"
                            "'s non-html pseudonym code, and the html pseudonym of <del>"
                            "<b style=\"color:#00FF00\">&lt;i&gt;Escaped HTML pseudonym&lt;/i&gt;</b>"
                            "</del> I mean "
                            "<b style=\"color:#00FF00\"><!--HTML--><i>Unescaped HTML pseudonym</i></b>"
                            "(also ensuring pseudonym codes aren't interpreted as hyperlinks).")
        assert reports[(p[0] + " identifier", 0)] == (
            "<p>Testing <strong>markdown</strong> in reports and interaction "
            "with <em><b style=\"color:#00FF00\">Test pseudonym</b></em>&#x27;s pseudonym code.</p>"
        )
        assert reports[(p[1] + " identifier", 0)] == (
            "<p>Testing<br />\n"
            "multiline</p>\n"
            "<p>reports.</p>"
        )
        assert reports[(p[1] + " identifier", 1)] == (
            "<!--HTML-->Testing that markdown is **ignored** in HTML-enabled reports.\n"
            "Including:\n\n"
            "Leaving newlines as-is."
        )
