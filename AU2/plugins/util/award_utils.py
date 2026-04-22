"""Shared functions for dealing with awards"""
import re

AWARD_PAGES_FILENAME = "awards.html"

# the required format for archive game folders, according to archive_collated_awards.php
GAME_NAME_PATTERN = re.compile(r"^[0-9]{4}-[a-z]*$")
# finds the list of awards as encoded for the collated awards page which occurs in an HTML comment starting with AWARDS:
AWARD_DATA_PATTERN = re.compile(r"<!--.*?AWARDS:(.*?)-->", flags=re.DOTALL)
# parses each individual line giving the recipient of an award
AWARD_LINE_PATTERN = re.compile(r" *The (?P<award_name>.*) for (?P<award_type>.*) *: *(?P<winner>[^:]*)$")
# matches the CSS defining the colour for an award in award_colours.css
AWARD_COLOUR_PATTERN = re.compile(r"\.(?P<award_key>[a-zA-Z]+\s*{[^}]*color\s*:\s*(?P<award_colour>\S+)\s*;})")

# regex patterns from archive_collated_awards.php
AWARD_NAME_PATTERN = re.compile(r"^ *The (.*) for (.*) *$", flags=re.IGNORECASE)
KEY_TRANSFORMATION_PATTERN = re.compile(r"[^A-Za-z]+")

# pattern to ignore an initial 'The'
INITIAL_THE_PATTERN = re.compile(r"^\s*The ", flags=re.IGNORECASE)


def parse_award_name(full_name: str) -> (str, str):
    """Parses a full award name into the format used internally by AwardsPlugin

    Args:
        full_name (str): Full award name. Must be of form "The X for Y".

    Returns:
        str, str: the tuple (X, Y)

    Examples:
        >>> parse_award_name("The 'Ginger Cake' Award for the 'Smoothest' Kill")
        ("'Ginger Cake' Award", "the 'Smoothest' Kill")
    """
    m = AWARD_NAME_PATTERN.match(full_name)
    return m[1], m[2]


def render_award_name(name: (str, str)) -> str:
    """A (right) inverse of `parse_award_name`"""
    return f"The {name[0]} for {name[1]}"


def award_type_to_key(award_type: str) -> str:
    """Converts an award reason (part of the award name after 'for') into the corresponding key used as its CSS class,
    and by archive_collated_awards.php to count two awards as 'the same' and to link from that page to the original
    award.

    Args:
        award_type (str): The part of an award name after 'for', defining the award.

    Returns:
        str: the award's "key"

    Examples:
        >>> award_type_to_key("the 'Smoothest' Kill")
        'thesmoothestkill'
    """
    return KEY_TRANSFORMATION_PATTERN.sub("", award_type).lower()
