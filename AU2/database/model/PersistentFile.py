import os
from dataclasses_json import dataclass_json


@dataclass_json
class PersistentFile:
    WRITE_LOCATION = ""
    TEST_MODE = False

    def __hash__(self):
        return hash(self.get_id())

    @classmethod
    def toggle_test_mode(cls, test_mode: bool):
        cls.TEST_MODE = test_mode

    def save(self):
        # don't save while doing tests
        if self.test_mode:
            return
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
