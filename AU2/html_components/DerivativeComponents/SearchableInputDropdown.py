from typing import Optional, List

from AU2.html_components.MetaComponents.Searchable import Searchable
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown

class SearchableInputDropdown(Searchable):

    name = "SearchableInputDropdown"

    def __init__(self, identifier: str, title: str, options: List[str], selected: Optional[str] = None):
        def searchable_setter(component, new_options):
            """Setter for Searchable that ensures the default selection is included in search results"""
            component.options = new_options
            if component.selected and component.selected not in new_options:
                component.options.append(component.selected)

        super().__init__(
            InputWithDropDown(
                identifier=identifier,
                title=title,
                options=options,
                selected=selected
            ),
            title=f"{title} (Search)",
            accessor=lambda i: i.options,
            setter=searchable_setter
        )
