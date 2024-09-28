from html import escape


class HTMLComponent:
    # Map from a component name to its decoder
    __decoders = {}

    identifier: str
    uniqueId = 0

    name = "abstract_HTMLComponent"

    # whether a component requires user interaction (no: label, yes: textbox)
    noInteraction = False

    def __init__(self):
        self.__decoders[self.name] = self.__class__

    def render(self) -> str:
        return f"""<div class="{escape(self.name)}">{self._representation()}</div>"""

    def _representation(self) -> str:
        """
        Renders this component as HTML
        :return: the html rendering of this component
        """
        raise NotImplementedError()

    @classmethod
    def parse(self, html: str) -> 'HTMLComponent':
        """
        Parses the appropriate HTML string into a component
        :param html: the actual HTMl div to parse back into a component
        :return: an instance of this class
        """
        raise NotImplementedError()

    @classmethod
    def get_unique_str(cls) -> str:
        t = cls.uniqueId
        cls.uniqueId += 1
        return str(t)
