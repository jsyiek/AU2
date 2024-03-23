import os

BASE_WRITE_LOCATION = os.path.expanduser("~/database")
ASSASSINS_WRITE_LOCATION = os.path.join(BASE_WRITE_LOCATION, "AssassinsDatabase.json")
EVENTS_WRITE_LOCATION = os.path.join(BASE_WRITE_LOCATION, "EventsSummary.json")
GENERIC_STATE_WRITE_LOCATION = os.path.join(BASE_WRITE_LOCATION, "GenericState.json")