from AU2.html_components.HiddenComponent import HiddenComponent


class HiddenTextbox(HiddenComponent[str]):
    name: str = "HiddenTextbox"

    def _representation(self) -> str:
        return f"""
            <input type="hidden" id="{self.identifier}" value="{self.default}">
        """
