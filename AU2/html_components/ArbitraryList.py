from html import escape
from typing import List

from AU2.html_components import HTMLComponent


class ArbitraryList(HTMLComponent):
    name: str = "ArbitraryList"

    def __init__(self, identifier: str, title: str, values: List[str]):
        self.title = escape(title)
        self.identifier = escape(identifier)
        self.uniqueStr = self.get_unique_str()
        self.values = [escape(a) for a in values]
        super().__init__()

    def _representation(self) -> str:
        items = "".join(f"addItem('{v}');\n" for v in self.values)
        return f"""
            <label for="{self.identifier}">{self.title}</label>
            <div id="{self.identifier}"></div>""" + """\n<button id="add-item-button">Add Item</button>
        
            <script>
                document.getElementById('add-item-button').addEventListener('click', function() {
                    addItem();
                });
        
                function addItem(value = '') {"""+\
                    f"""const entryList = document.getElementById('{self.identifier}');""" +\
                    """const itemDiv = document.createElement('div');
                    itemDiv.className = 'item';
        
                    const itemInput = document.createElement('input');
                    itemInput.type = 'text';
                    itemInput.value = value;
        
                    const deleteButton = document.createElement('button');
                    deleteButton.textContent = 'Delete';
                    deleteButton.addEventListener('click', function() {
                        entryList.removeChild(itemDiv);
                    });
        
                    itemDiv.appendChild(itemInput);
                    itemDiv.appendChild(deleteButton);
                    entryList.appendChild(itemDiv);
                }
        
                // Add default entry""" + items + """</script>"""
