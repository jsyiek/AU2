from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox


class AwardNameEntry(DefaultNamedSmallTextbox):
    """A special component that implements validation for the Award name format (The X Award for Y).
    Validation is also done in the back-end, so this can be rendered as a `DefaultNamedSmallTextbox` as a fallback."""
    name: str = "AwardNameEntry"

    def __init__(self, *args, suggestions = (), **kwargs):
        super().__init__(*args, **kwargs)
        self.suggestions = suggestions