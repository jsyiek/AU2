import os

from AU2 import BASE_WRITE_LOCATION
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.database.LocalConfigDatabase import LOCAL_CONFIG_DATABASE

if not os.path.exists(BASE_WRITE_LOCATION):
    os.makedirs(BASE_WRITE_LOCATION, exist_ok=True)


def save_all_databases():
    ASSASSINS_DATABASE.save()
    EVENTS_DATABASE.save()
    GENERIC_STATE_DATABASE.save()
    LOCAL_CONFIG_DATABASE.save()
