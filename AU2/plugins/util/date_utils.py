import datetime
from typing import Optional

from AU2 import TIMEZONE


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