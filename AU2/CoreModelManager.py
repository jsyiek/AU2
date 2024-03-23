from AU2.database.database import ASSASSINS_DATABASE, save_database
from AU2.database.model import Assassin
from AU2.plugins.ConfigLoader import PLUGINS


def add_assassin(assassin: Assassin):
    for p in PLUGINS:
        p.on_assassin_create(assassin)
    ASSASSINS_DATABASE.add(assassin)


def delete_assassin(assassin: Assassin):
    for p in PLUGINS:
        p.on_assassin_delete(assassin)
    ASSASSINS_DATABASE.delete(assassin)


def save():
    save_database()
