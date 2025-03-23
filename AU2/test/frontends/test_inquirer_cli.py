"""unit tests for `inquirer_cli"""
from AU2.frontends.inquirer_cli import html_validator


def test_html_validator():
    assert html_validator(None, "<b>This</b> is <i>valid</i> HTML.")
    assert not html_validator(None, "<p><b>This is invalid HTML.</p></b>")
