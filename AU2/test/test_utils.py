import datetime
from typing import List

from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import PersistentFile, Assassin, Event
from AU2.database.model.database_utils import refresh_databases
from AU2.plugins.util import random_data


def plugin_test(f):
    """
    Wraps a test function with functionality to clear the databases
    """
    def plugin_test_impl(*args, **kwargs):
        PersistentFile.toggle_test_mode(test_mode=True)
        refresh_databases()
        f(*args, **kwargs)
        PersistentFile.toggle_test_mode(test_mode=False)
        # explicitly don't refresh the databases to avoid repeatedly reloading from disk

    return plugin_test_impl


def some_players(num: int) -> List[str]:
    """
    Returns some random assassin names

    Parameters:
        num (int): How many names to return

    Returns:
         List[str]: list of assassin names
    """
    if num > len(random_data.all_names):
        raise Exception("Not enough names")
    return random_data.all_names[0:num]


class MockGame:


    def __init__(self):
        self.date = datetime.datetime(year=2022, month=9, day=1, hour=10, minute=0, second=0)
        self.assassins = list()

    def has_died(self, name):
        if name in self.assassins:
            self.assassins.remove(name)

    def get_remaining_players(self):
        return list(self.assassins)

    def new_datetime(self) -> datetime.datetime:
        old_date = self.date
        self.date = self.date + datetime.timedelta(days=1)
        return old_date

    def having_assassins(self, names: List[str]) -> "MockGame":
        """
        Fills out the assassins database with some assassin objects based on the input names

        Parameters:
            names (List[str]): List of assassin names

        Returns:
            self (to facilitate chaining
        """
        self.assassins = list(names)

        for n in names:
            a = Assassin(
                pseudonyms=[n + " pseudonym"],
                real_name=n,
                pronouns=n + " pronouns",
                email=n + " email",
                address=n + " address",
                water_status=n + " water status",
                college=n + " college",
                notes=n + " notes ",
                is_police=False
            )
            ASSASSINS_DATABASE.add(a)

        return self

    def assassin(self, name: str):
        """
        Returns a ProxyAssassin object for that name
        """

        return ProxyAssassin(self, name)


class ProxyAssassin:
    """
    Proxy object of one or more assassins to facilitate readable tests
    """
    def __init__(self, mockGame: "MockGame", *assassins: str):
        self.mockGame = mockGame
        self.assassins = assassins

    def __ident(self, name):
        return name + " identifier"

    def are_police(self) -> MockGame:
        """
        Makes these assassins police
        """
        for a in self.assassins:
            ASSASSINS_DATABASE.assassins[self.__ident(a)].is_police = True

        return self.mockGame

    def is_police(self):
        """
        Makes this assassin a police
        """
        return self.are_police()

    def with_accomplices(self, *others: str) -> "ProxyAssassin":
        """
        Adds several accomplices to the proxy assassin

        Parameters:
            others (str...): Other assassins to accomplice
        """
        return ProxyAssassin(self.mockGame, *(self.assassins + others))

    def and_these(self, *others: str) -> "ProxyAssassin":
        """
        See ProxyAssassin.withAccomplices
        """
        return self.with_accomplices(*others)

    def kills(self, *victims: str) -> MockGame:
        """
        Submits an event to the Events database where this assassin (with accomplice help) kills (an)other(s)

        Parameters:
            victims (str...): Victims

        Returns:
            MockGame: the original mock game from where this assassin was created
        """

        participants = self.assassins + victims
        e = Event(
            assassins={self.__ident(p) : 0 for p in participants},
            datetime=self.mockGame.new_datetime(),
            headline="Event Headline",
            reports=[],
            kills=[(self.__ident(self.assassins[0]), self.__ident(v)) for v in victims]
        )
        EVENTS_DATABASE.add(e)

        for v in victims:
            self.mockGame.has_died(v)

        return self.mockGame
