import os

import pytz

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_WRITE_LOCATION = os.path.expanduser("~/database")

TIMEZONE = pytz.timezone("Europe/London")
