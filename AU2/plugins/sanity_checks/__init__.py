from typing import Dict

from AU2.plugins.sanity_checks.IncorrectPseudonymFormatter import IncorrectPseudonymFormatter
from AU2.plugins.sanity_checks.MissingHtmlSpecifier import MissingHtmlSpecifier
from AU2.plugins.sanity_checks.PlayerNotDead import PlayerNotDead

SANITY_CHECKS: Dict[str, "SanityCheck"] = {
    "Missing_HTML_Specifiers": MissingHtmlSpecifier(),
    "Incorrect_Pseudonym_Formatter": IncorrectPseudonymFormatter(),
    "Player_Not_Dead": PlayerNotDead()
}
