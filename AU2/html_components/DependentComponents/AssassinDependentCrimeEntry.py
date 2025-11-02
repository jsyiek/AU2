from typing import Dict, List, Tuple

from AU2.html_components import HTMLComponent


class AssassinDependentCrimeEntry(HTMLComponent):
    name: str = "AssassinDependentCrimeEntry"

    def __init__(self, pseudonym_list_identifier: str, identifier: str, title: str,
                 default: Dict[str, Tuple[int, str, str]], kill_entry_identifier: str,
                 targeting_graph: Dict[str, List[str]]):
        self.pseudonym_list_identifier = pseudonym_list_identifier
        self.title = title
        self.identifier = identifier
        self.uniqueStr = self.get_unique_str()
        self.default = default
        self.kill_entry_identifier = kill_entry_identifier
        self.targeting_graph = targeting_graph
        super().__init__()

    def _representation(self) -> str:
        raise NotImplementedError()
