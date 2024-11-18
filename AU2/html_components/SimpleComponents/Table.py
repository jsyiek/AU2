from typing import List, Optional

from AU2.html_components import HTMLComponent


class Table(HTMLComponent):

    name = "Table"
    noInteraction: bool = True

    def __init__(self, rows: List[List[str]], headings: List[str] = []):
        self.identifier = "Table" # needed for compatibility but not strictly relevant
        self.rows = rows
        self.headings = headings
        super().__init__()

    def _representation(self) -> str:
        tbody = "\n".join("<tr>" + "\n".join(f"<td>{d}</td>" for d in r) + "</tr>" for r in self.rows)
        thead = "<tr>" + "\n".join(f"<th>{d}</th>" for d in self.headings) + "</tr>"
        return f"""<table>
    <thead>{thead}</thead>
    <tbody>{tbody}</tbody>
</table>"""
