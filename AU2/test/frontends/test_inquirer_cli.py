"""unit tests for `inquirer_cli"""
from AU2.frontends.inquirer_cli import html_validator, soft_html_validator


def test_html_validator():
    assert html_validator(None, "<b>This</b> is <i>valid</i> HTML.")
    assert html_validator(
        None,
        "<audio controls=\"controls\"><source src=\"./imgL2025/121_Noot_noot.mp3\" type=\"audio/mpeg\"></audio>"
    )
    assert not html_validator(None, "<p>This is <b>invalid</p> HTML.</b>")


def test_soft_html_validator():
    assert html_validator(None, "<!--HTML--> <b>This</b> is <i>valid</i> HTML.")
    assert not html_validator(None, "<!--HTML--> <p><b>This is invalid HTML.</p></b>")
    assert soft_html_validator(None, "<p><b>This is invalid HTML, but we don't care because it will be escaped</p></b>")
    assert soft_html_validator(
        None,
        "<!--HTML--><audio controls=\"controls\"><source src=\"./imgL2025/121_Noot_noot.mp3\" type=\"audio/mpeg\"></audio>"
    )
