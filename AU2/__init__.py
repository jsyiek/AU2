import os
import pathlib

import pytz

ROOT_DIR = pathlib.Path(os.path.abspath(__file__)).parent
BASE_WRITE_LOCATION = pathlib.Path(os.path.expanduser("~/database"))
TIMEZONE = pytz.timezone("Europe/London")

# Sets the encoding to utf-8 for pyinquirer on Windows machines, since that isn't the default for some reason
if os.name == "nt":
    pathlib_open = pathlib.Path.open
    def pathlib_open_utf8(*args, **kwargs):
        # 'b' means to open a file in 'byte' mode, so we can't use an encoding in this case
        if "b" not in kwargs.get("mode", "") and "b" not in (args[1] if len(args) > 1 else ""):
            kwargs["encoding"] = "utf-8"
        return pathlib_open(*args, **kwargs)
    pathlib.Path.open = pathlib_open_utf8
