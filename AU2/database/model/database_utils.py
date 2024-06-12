from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE


def refresh_databases():
    ASSASSINS_DATABASE._refresh()
    EVENTS_DATABASE._refresh()
    GENERIC_STATE_DATABASE._refresh()
