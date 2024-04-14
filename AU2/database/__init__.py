import os

from AU2 import BASE_WRITE_LOCATION

if not os.path.exists(BASE_WRITE_LOCATION):
    os.makedirs(BASE_WRITE_LOCATION, exist_ok=True)

# if __name__ == "__main__":
#     # Testing code
#     assassin = Assassin(["Vendetta"], "Ben", "bms53@cam.ac.uk", "Homerton", "No water", "Homerton", "No attacking in a suit", False)
#     ASSASSINS_DATABASE.add(assassin)
#     print(ASSASSINS_DATABASE)
#     ASSASSINS_DATABASE.dump_json()
