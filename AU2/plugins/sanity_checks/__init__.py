from typing import Dict

from AU2.plugins.sanity_checks.MissingHtmlSpecifier import MissingHtmlSpecifier
from AU2.plugins.sanity_checks.model.SanityCheck import SanityCheck

SANITY_CHECKS: Dict[str, SanityCheck] = {
    "Missing_HTML_Specifiers": MissingHtmlSpecifier()
}
