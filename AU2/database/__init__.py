import os

from AU2 import BASE_WRITE_LOCATION

if not os.path.exists(BASE_WRITE_LOCATION):
    os.makedirs(BASE_WRITE_LOCATION, exist_ok=True)

ALL_DATABASES = []


def save_all_databases():
    for database in ALL_DATABASES:
        database.save()


def refresh_databases():
    for database in ALL_DATABASES:
        database._refresh()
