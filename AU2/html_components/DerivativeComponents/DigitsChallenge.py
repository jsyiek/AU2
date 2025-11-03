import random

from typing import List

from AU2.html_components.HTMLComponent import HTMLComponent
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.NamedSmallTextbox import NamedSmallTextbox


def DigitsChallenge(identifier_prefix: str, title: str) -> List[HTMLComponent]:
    """
    Produces components for a 'challenge' requiring the user to repeat specified digits for confirmation of a
    dangerous action, e.g. (resetting the database or deleting an event)

    Args:
        identifier_prefix (str): prefix to use for component identifiers
        title (str): Text to prompt the user with. Include {digits} where the digits to be copied should be displayed.

    Returns:
        List[HTMLComponent]: a list containing a HiddenTextbox storing some random digits, and a NamedSmallTextbox
            whose title is `title` with {digits} replaced by those random digits.
    """
    i = random.randint(0, 1000000)
    return [
        HiddenTextbox(
            identifier=identifier_prefix + "_DigitsChallenge_HiddenTextbox",
            default=str(i)
        ),
        NamedSmallTextbox(
            identifier=identifier_prefix + "_DigitsChallenge_NamedSmallTextbox",
            title=title.format(digits=i)
        ),
    ]


def read_DigitsChallenge(identifier_prefix: str, html_response: dict) -> bool:
    """
    Reads the response from a pair of components produced by DigitsChallenge.

    Args:
        identifier_prefix (str): prefix that was passed to DigitsChallenge to create the components
        html_response (dict): the response from processing components

    Returns
        bool: whether or not the user completed the challenge successfully
    """
    return html_response[identifier_prefix + "_DigitsChallenge_HiddenTextbox"] == html_response[identifier_prefix + "_DigitsChallenge_NamedSmallTextbox"]

