import datetime
from typing import Optional, NamedTuple

from AU2 import TIMEZONE
from AU2.plugins.constants import TERM_MAP

DATETIME_FORMAT = "%Y-%m-%d %H:%M"

PRETTY_DATETIME_FORMAT = "%d %b, %H:%M %p"


def get_now_dt():
   return datetime.datetime.now().astimezone(TIMEZONE)


# global datetime <-> timestamp conversion functions to ensure consistency
# supports "optional datetimes" comnverting `None` to `None`
def timestamp_to_dt(ts: Optional[float]) -> Optional[datetime.datetime]:
   if ts is None:
      return None
   return datetime.datetime.fromtimestamp(ts).astimezone().astimezone(TIMEZONE)


def dt_to_timestamp(ts: Optional[datetime.datetime]) -> Optional[float]:
   if ts is None:
      return None
   return ts.timestamp()


WeekAndDay = NamedTuple("WeekAndDay", [
   ("days_since_start", int),
   ("week", int),
   ("day_of_week", int)
])


def date_to_weeks_and_days(start: datetime.date, date: datetime.date) -> WeekAndDay:
    """
    Converts param `date` into a namedtuple `WeekAndDay` of:
        - days_since_start: number of days since param `start`
        - week: week number (week starting on param `start` is week 1)
        - day_of_week: day number in week (taking values 0 to 6 inclusive)
    """
    days_since_start = (date - start).days
    week = days_since_start // 7 + 1
    day = days_since_start % 7
    if week < 0:
        week = 0
        day = days_since_start + 7
    return WeekAndDay(days_since_start, week, day)


def weeks_and_days_to_str(start: datetime.date, week: int, day: int) -> str:
    """
    Converts a 1-indexed week and a 0-indexed day into a string for news webpage

    It might seem counterintuitive to make the days and weeks different indexing.
    This is because week 0 news takes place the week before the game starts.
    This is usually rendered as a bounty.
    """
    return (start + datetime.timedelta(days=day, weeks=week-1)).strftime("%A, %d %B")


def datetime_to_time_str(event_time: datetime.datetime) -> str:
    """
    Returns a formatted timestamp suitable for the news.
    """
    return event_time.strftime("%H:%M %p")


def get_term(ts: datetime.datetime) -> str:
    """
    Returns the term name for a particular datetime, based on month.
    """
    return f'{TERM_MAP.get(ts.month, "???")} {ts.year}'


def archive_game_name_to_tuple(game_name: str) -> (int, int):
    """
    Converts the game names as used in the archive to tuples that when ordered lexicographically correspond to the
    chronological order of games.

    Args:
        game_name (str): Name of a game as appears in the archives, i.e. of the form '2019-mich'

    Returns:
        (int, int): a tuple of (year, term number), where for term number, lent -> 0, mw -> 1, mich -> 2.

    Examples:
        >>> archive_game_name_to_tuple('2019-mich')
        (2019, 2)
        >>> archive_game_name_to_tuple('2020-lent')
        (2020, 0)
        >>> archive_game_name_to_tuple('2025-mw')
        (2025, 1)
    """
    year, term = game_name.split("-", 1)
    term_as_int = 0 if term == 'lent' else 2 if term == 'mich' else 1
    return int(year), term_as_int
