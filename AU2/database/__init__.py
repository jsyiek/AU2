import os

from AU2 import BASE_WRITE_LOCATION
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE

if not os.path.exists(BASE_WRITE_LOCATION):
    os.makedirs(BASE_WRITE_LOCATION, exist_ok=True)


def save_all_databases():
    ASSASSINS_DATABASE.save()
    EVENTS_DATABASE.save()
    GENERIC_STATE_DATABASE.save()


# if __name__ == "__main__":
#     # Testing code
#     assassin = Assassin(["Vendetta"], "Ben", "bms53@cam.ac.uk", "Homerton", "No water", "Homerton", "No attacking in a suit", False)
#     ASSASSINS_DATABASE.add(assassin)
#     print(ASSASSINS_DATABASE)
#     ASSASSINS_DATABASE.dump_json()
