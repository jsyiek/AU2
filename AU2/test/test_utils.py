import datetime
from typing import List

from AU2 import TIMEZONE
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.model import PersistentFile, Assassin, Event
from AU2.database.model.database_utils import refresh_databases
from AU2.plugins.util import random_data
from AU2.plugins.util.date_utils import get_now_dt


def dummy_event():
    """
    assassins: Dict[str, int]
    datetime: datetime.datetime
    headline: str
    reports: List[Tuple[str, int, str]]
    kills: List[Tuple[str, str]]
    pluginState: Dict[str, Any] = field(default_factory=dict)
    """
    return Event(
        assassins={},
        datetime=get_now_dt(),
        headline="",
        reports=[],
        kills={},
        pluginState={}
    )


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


class Database:

    @staticmethod
    def has_assassin(assassin: str):
        assert assassin + " identifier" in ASSASSINS_DATABASE.assassins, "Not in database"
        return AssassinValidator(ASSASSINS_DATABASE.assassins[assassin + " identifier"])

    @classmethod
    def doesnt_have_assassin(cls, assassin: str):
        assert assassin + " identifier" not in ASSASSINS_DATABASE.assassins, "In database"
        return cls

    @classmethod
    def has_no_events(cls):
        return cls.has_events(0)

    @classmethod
    def has_events(cls, num: int):
        assert len(EVENTS_DATABASE.events) == num
        return cls

class AssassinValidator:
    def __init__(self, assassin):
        self.assassin = assassin

    @property
    def having(self):
        assassin = self.assassin
        outer = self

        class Having:
            def __getattribute__(self, var: str):
                if var == "having":
                    return self
                return lambda expected: outer.check(assassin.__getattribute__(var), expected, self)

        return Having()

    def check(self, actual, expected, having):
        assert actual == expected
        return having


class MockGame:


    def __init__(self):
        self.date = datetime.datetime(year=2022, month=9, day=1, hour=10, minute=0, second=0).astimezone(TIMEZONE)
        self.assassins = list()

    def has_died(self, name):
        if name in self.assassins:
            self.assassins.remove(name)

    def get_remaining_players(self):
        return list(self.assassins)

    def refresh_deaths_from_db(self):
        for e in list(EVENTS_DATABASE.events.values()):
            for (_, victim) in e.kills:
                # Hacky trimming because MockGame.assassins stores names, not identifiers for some reason
                victim_name = victim[:-11]
                if victim_name in self.assassins:
                    self.assassins.remove(victim_name)

    def new_datetime(self) -> datetime.datetime:
        old_date = self.date
        self.date = self.date + datetime.timedelta(minutes=1)
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

    def are_hidden(self) -> MockGame:
        """
        Makes these assassins hidden
        """
        for a in self.assassins:
            ASSASSINS_DATABASE.assassins[self.__ident(a)].hidden = True

        return self.mockGame

    def is_hidden(self):
        """
        Makes this assassin hidden
        """
        return self.are_hidden()

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
        self.mockGame = self.is_involved_in_event(assassins=victims,
                                                  kills=[(self.__ident(self.assassins[0]), self.__ident(v)) for v in
                                                         victims],
                                                  pluginState={"CompetencyPlugin": {"competency": {self.__ident(a): 14 for a in self.assassins}}})

        for v in victims:
            self.mockGame.has_died(v)

        return self.mockGame

    def is_involved_in_event(self, assassins=None, dt=None, headline="Event Headline", reports=None, kills=None, pluginState=None):
        """
        Submits a generic event to the database

        Parameters:
            assassins list(str): Additional assassins
            dt datetime.datetime: Datetime of event
            headline str: Headline
            reports list(str): Reports
            kills list(tuple(str, str)): Kills
            pluginState: dict: Plugin State

        Returns:
            MockGame: the original mock game from where this assassin was created
        """
        participants = self.assassins
        if assassins is not None:
            participants += assassins

        e = Event(
            assassins={self.__ident(p) : 0 for p in participants},
            datetime=dt if dt is not None else self.mockGame.new_datetime(),
            headline=headline,
            reports=reports if reports is not None else [],
            kills=kills if kills is not None else [],
            pluginState=pluginState if pluginState is not None else {}
        )
        EVENTS_DATABASE.add(e)

        return self.mockGame