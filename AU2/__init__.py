import os

import pytz

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_WRITE_LOCATION = os.path.expanduser("~/database")
TIMEZONE = pytz.timezone("Europe/London")

# Sets the encoding to utf-8 for pyinquirer on Windows machines, since that isn't the default for some reason
if os.name == "nt":
    import pathlib

    pathlib_open = pathlib.Path.open
    def pathlib_open_utf8(*args, **kwargs):
        if "b" not in kwargs.get("mode", "") and "b" not in (args[1] if len(args) > 1 else ""):
            kwargs["encoding"] = "utf-8"
        return pathlib_open(*args, **kwargs)
    pathlib.Path.open = pathlib_open_utf8
