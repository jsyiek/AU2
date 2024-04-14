import os
from dataclasses_json import dataclass_json


@dataclass_json
class PersistentFile:
    WRITE_LOCATION = ""

    def __hash__(self):
        return hash(self.get_id())

    def save(self):
        dump = self.to_json()
        with open(self.WRITE_LOCATION, "w+") as F:
            F.write(dump)

    @classmethod
    def load(cls):
        if os.path.exists(cls.WRITE_LOCATION):
            with open(cls.WRITE_LOCATION, "r") as F:
                dump = F.read()
            return cls.from_json(dump)
        return cls({})
