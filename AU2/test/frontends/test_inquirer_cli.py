"""unit tests for `inquirer_cli"""
import pytest

from inquirer.errors import ValidationError

from AU2.frontends.inquirer_cli import html_validator, soft_html_validator


class TestInquirerCli:
    def test_html_validator(self):
        assert html_validator(None, "<b>This</b> is <i>valid</i> HTML.")
        assert html_validator(
            None,
            "<audio controls=\"controls\"><source src=\"./imgL2025/121_Noot_noot.mp3\" type=\"audio/mpeg\"></audio>"
        )
        with pytest.raises(ValidationError):
            html_validator(None, "<p>This is <b>invalid</p> HTML.</b>")
        with pytest.raises(ValidationError):
            html_validator(None, "<b unclosed ")
        with pytest.raises(ValidationError):
            html_validator(None, '<img src="unclosed/src/attribute.jpg />')
        assert html_validator(None, '<img src="correct/image/tag.jpg" />')

    def test_soft_html_validator(self):
        assert html_validator(None, "<!--HTML--> <b>This</b> is <i>valid</i> HTML.")
        with pytest.raises(ValidationError):
            html_validator(None, "<!--HTML--> <p><b>This is invalid HTML.</p></b>")
        assert soft_html_validator(None, "<p><b>This is invalid HTML, but we don't care because it will be escaped</p></b>")
        assert soft_html_validator(
            None,
            "<!--HTML--><audio controls=\"controls\"><source src=\"./imgL2025/121_Noot_noot.mp3\" type=\"audio/mpeg\"></audio>"
        )
