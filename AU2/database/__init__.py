import os

from AU2 import BASE_WRITE_LOCATION
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE

if not os.path.exists(BASE_WRITE_LOCATION):
    os.makedirs(BASE_WRITE_LOCATION, exist_ok=True)

UPLOAD_ORDER = (ASSASSINS_DATABASE, EVENTS_DATABASE, GENERIC_STATE_DATABASE)

def save_all_databases():
    for database in UPLOAD_ORDER:
        database.save()

def refresh_databases():
    for database in UPLOAD_ORDER:
        database._refresh()
