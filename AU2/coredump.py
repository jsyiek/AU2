import pickle
import platform
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class CoreDumpData:
    # Exception
    exception: Optional[Exception]
    exception_type: str
    exception_message: str
    traceback_text: str

    # Database snapshots (None if import failed)
    assassins_database: Optional[object]
    events_database: Optional[object]
    generic_state_database: Optional[object]

    # Environment / debug info
    au2_version: str
    python_version: str
    platform_info: str
    os_info: str
    timestamp: str
    working_directory: str
    database_location: str


def write_coredump(exception: Exception) -> str:
    """Write a coredump (text crash report + pickle) for an unhandled exception.

    Returns the path to the text crash report file.
    """
    # Defensively import AU2 constants -- crashes during AU2 import itself
    # should not prevent coredump generation.
    __version__ = "TBD" # pending future development work in AU2
    try:
        from AU2 import BASE_WRITE_LOCATION
    except Exception:
        BASE_WRITE_LOCATION = str(Path.home() / "database")

    # Defensively import each database singleton independently
    assassins_database = None
    try:
        from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
        assassins_database = ASSASSINS_DATABASE
    except Exception:
        pass

    events_database = None
    try:
        from AU2.database.EventsDatabase import EVENTS_DATABASE
        events_database = EVENTS_DATABASE
    except Exception:
        pass

    generic_state_database = None
    try:
        from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
        generic_state_database = GENERIC_STATE_DATABASE
    except Exception:
        pass

    Path(BASE_WRITE_LOCATION).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    stamp = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    

    base_coredump_location = Path(BASE_WRITE_LOCATION) / "coredumps"
    base_coredump_location.mkdir(parents=True, exist_ok=True)

    txt_path = str(base_coredump_location / f"coredump_{stamp}.txt")
    pkl_path = str(base_coredump_location / f"coredump_{stamp}.pkl")

    tb_text = traceback.format_exc()

    # Build CoreDumpData
    coredump_data = CoreDumpData(
        exception=exception,
        exception_type=type(exception).__name__,
        exception_message=str(exception),
        traceback_text=tb_text,
        assassins_database=assassins_database,
        events_database=events_database,
        generic_state_database=generic_state_database,
        au2_version=__version__,
        python_version=sys.version,
        platform_info=platform.platform(),
        os_info=f"{platform.system()} {platform.release()}",
        timestamp=timestamp.isoformat(),
        working_directory=str(Path.cwd()),
        database_location=BASE_WRITE_LOCATION,
    )

    # Attempt to pickle the coredump data
    pickle_status = _write_pickle(coredump_data, pkl_path)

    # Build and write the text crash report
    d = coredump_data
    lines = [
        "=== AU2 CRASH REPORT ===",
        "",
        f"Timestamp: {d.timestamp}",
        f"AU2 version: {d.au2_version}",
        f"Python version: {d.python_version}",
        f"Platform: {d.platform_info}",
        f"OS: {d.os_info}",
        f"Working directory: {d.working_directory}",
        f"Database location: {d.database_location}",
        "",
        f"Exception type: {d.exception_type}",
        f"Exception message: {d.exception_message}",
        "",
        "--- Traceback ---",
        d.traceback_text,
        "--- Pickle status ---",
        pickle_status,
        "",
    ]

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return txt_path


def _write_pickle(coredump_data: CoreDumpData, pkl_path: str) -> str:
    """Try to pickle the CoreDumpData with graduated fallback.

    Returns a status string for the text report.
    """
    # Phase 1: try as-is
    try:
        with open(pkl_path, "wb") as f:
            pickle.dump(coredump_data, f)
        return "Pickle written successfully (with traceback)."
    except Exception:
        pass

    # Phase 2: strip exception traceback
    try:
        if coredump_data.exception is not None:
            coredump_data.exception.__traceback__ = None
        with open(pkl_path, "wb") as f:
            pickle.dump(coredump_data, f)
        return "Pickle written successfully (traceback stripped)."
    except Exception:
        pass

    # Phase 3: strip database fields
    try:
        coredump_data.assassins_database = None
        coredump_data.events_database = None
        coredump_data.generic_state_database = None
        with open(pkl_path, "wb") as f:
            pickle.dump(coredump_data, f)
        return "Pickle written successfully (databases stripped)."
    except Exception:
        pass

    # Phase 4: strip exception entirely
    try:
        coredump_data.exception = None
        with open(pkl_path, "wb") as f:
            pickle.dump(coredump_data, f)
        return "Pickle written successfully (exception stripped)."
    except Exception as pkl_err:
        pass

    # Phase 5: give up, delete the pkl file
    try:
        Path(pkl_path).unlink()
    except OSError:
        pass
    return f"Pickle failed: {pkl_err}"
