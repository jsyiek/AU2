from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Dict, List

from AU2 import BASE_WRITE_LOCATION
from AU2.database.model import PersistentFile


_TEMPLATE_DEFAULTS: Dict[str, str] = {}


@dataclass_json
@dataclass
class TemplatesDatabase(PersistentFile):
    WRITE_LOCATION = BASE_WRITE_LOCATION / "TemplatesDatabase.json"
    templates: Dict[str, str]

    def set(self, template_identifier: str, template: str):
        self.templates[template_identifier] = template

    def reset(self, template_identifier: str):
        del self.templates[template_identifier]

    def get(self, template_identifier: str) -> str:
        return self.templates.get(template_identifier, _TEMPLATE_DEFAULTS.get(template_identifier))

    def register(self, template_identifier: str, template_default: str):
        _TEMPLATE_DEFAULTS[template_identifier] = template_default

    def list_templates(self) -> List[str]:
        return list(set(_TEMPLATE_DEFAULTS) | set(self.templates))

    def _refresh(self):
        """
        Forces a refresh of the underlying database
        """
        if self.TEST_MODE:
            self.templates = {}
            return

        self.assassins = self.load().templates


TEMPLATES_DATABASE = TemplatesDatabase.load()
