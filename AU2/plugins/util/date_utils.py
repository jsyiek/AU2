import datetime

from AU2 import TIMEZONE


def get_now_dt():
   return datetime.datetime.now().astimezone(TIMEZONE)