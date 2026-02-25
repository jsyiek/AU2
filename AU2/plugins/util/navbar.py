from typing import List, NamedTuple

from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION


LIST_ITEM_TEMPLATE = """<li><a href="{URL}">{DISPLAY}</a></li>\n"""

NavbarEntry = NamedTuple("NavbarEntry", (("url", str), ("display", str), ("position", float)))


def generate_navbar(navbar_entries: List[NavbarEntry], filename: str):
    """
    Generates a html list of page links, for inclusion into header.html using `w3-include-html`.

    Args:
        navbar_entries (list(NavbarEntry)): each NavberEntry namedtuple specifies a url, display text, and position.
            The position is a float value and the entries are rendered from top to bottom in *ascending* order of
            position.
        filename (str): the filename to save the list under (in the WEBPAGE_WRITE_LOCATION directory).
    """
    with open(WEBPAGE_WRITE_LOCATION / filename, "w+", encoding="utf-8", errors="ignore") as f:
        f.write("\n".join(
            LIST_ITEM_TEMPLATE.format(
                URL=entry.url,
                DISPLAY=entry.display
            ) for entry in sorted(navbar_entries, key=lambda e: e.position)
        ))