from AU2.html_components.HTMLComponent import HTMLComponent

class DigitsChallenge(HTMLComponent):
    """
    Component for a 'challenge' requiring the user to repeat specified digits for confirmation of a dangerous action,
    e.g. (resetting the database or deleting an event)

    Attributes:
        identifier (str): string to identify the component in the response
        title (str): Text to prompt the user with. Include {digits} where the digits to be copied should be displayed.
    """
    name: str = "DigitsChallenge"

    def __init__(self, identifier: str, title: str):
        # validate that can `title` includes the {digits} formatting code
        # (.format will work regardless, but the component doesn't make sense without including the digits to repeat!)
        if "{digits}" not in title:
            raise ValueError(f"DigitsChallenge title '{title}' does not contain '{{digits}}'.")
        self.title = title
        self.identifier = identifier
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
