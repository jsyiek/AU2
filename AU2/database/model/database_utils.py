from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.LocalDatabase import LOCAL_DATABASE


def refresh_databases():
    ASSASSINS_DATABASE._refresh()
    EVENTS_DATABASE._refresh()
    GENERIC_STATE_DATABASE._refresh()
    LOCAL_DATABASE._refresh()


def is_database_file(filename: str, include_local: bool = False) -> bool:
    return filename.endswith(".json") and (include_local or not filename.startswith("__"))
