import datetime
from typing import Optional, NamedTuple

from AU2 import TIMEZONE

DATETIME_FORMAT = "%Y-%m-%d %H:%M"


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
