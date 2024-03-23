import os

from AU2.database import ASSASSINS_WRITE_LOCATION, BASE_WRITE_LOCATION, EVENTS_WRITE_LOCATION, \
    GENERIC_STATE_WRITE_LOCATION
from AU2.database.model import AssassinsDatabase, EventsDatabase, GenericStateDatabase, Assassin

ASSASSINS_DATABASE = AssassinsDatabase({})
EVENTS_DATABASE = EventsDatabase({})
GENERIC_STATE_DATABASE = GenericStateDatabase({})

if not os.path.exists(BASE_WRITE_LOCATION):
    os.makedirs(BASE_WRITE_LOCATION, exist_ok=True)

if os.path.exists(ASSASSINS_WRITE_LOCATION):
    with open(ASSASSINS_WRITE_LOCATION) as A:
        assassins = A.read()
    ASSASSINS_DATABASE = AssassinsDatabase.from_json(assassins)

if os.path.exists(EVENTS_WRITE_LOCATION):
    with open(EVENTS_WRITE_LOCATION) as E:
        events = E.read()
    EVENTS_DATABASE = EventsDatabase.from_json(events)

if os.path.exists(GENERIC_STATE_WRITE_LOCATION):
    with open(GENERIC_STATE_WRITE_LOCATION) as G:
        state = G.read()
    GENERIC_STATE_DATABASE = GenericStateDatabase.from_json(state)

if __name__ == "__main__":
    assassin = Assassin(["Vendetta"], "Ben", "bms53@cam.ac.uk", "Homerton", "No water", "Homerton", "No attacking in a suit", False)
    ASSASSINS_DATABASE.add(assassin)
    print(ASSASSINS_DATABASE)
    ASSASSINS_DATABASE.dump_json()
