import pickle
import tempfile
from pathlib import Path
from unittest.mock import patch

from AU2.coredump import CoreDumpData, write_coredump


def _call_write_coredump(exception):
    """Helper: call write_coredump from inside an except block so
    traceback.format_exc() has active context."""
    try:
        raise exception
    except Exception as e:
        return write_coredump(e)


class TestCoreDump:

    def test_creates_txt_and_pkl_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("AU2.BASE_WRITE_LOCATION", tmpdir):
                txt_path = _call_write_coredump(RuntimeError("boom"))

            assert Path(txt_path).is_file()
            pkl_path = Path(txt_path).with_suffix(".pkl")
            assert Path(pkl_path).is_file()

    def test_txt_contains_required_sections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("AU2.BASE_WRITE_LOCATION", tmpdir):
                txt_path = _call_write_coredump(ValueError("test error"))

            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()

            assert "=== AU2 CRASH REPORT ===" in content
            assert "AU2 version:" in content
            assert "Python version:" in content
            assert "Platform:" in content
            assert "Exception type: ValueError" in content
            assert "Exception message: test error" in content
            assert "Traceback" in content
            assert "Pickle status" in content

    def test_pkl_can_be_unpickled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("AU2.BASE_WRITE_LOCATION", tmpdir):
                txt_path = _call_write_coredump(RuntimeError("round trip"))

            pkl_path = Path(txt_path).with_suffix(".pkl")
            with open(pkl_path, "rb") as f:
                loaded = pickle.load(f)

            assert isinstance(loaded, CoreDumpData)
            assert isinstance(loaded.exception, RuntimeError)
            assert str(loaded.exception) == "round trip"
            assert loaded.exception_type == "RuntimeError"
            assert loaded.exception_message == "round trip"
            assert isinstance(loaded.au2_version, str)
            assert isinstance(loaded.python_version, str)

    def test_unpicklable_exception_graceful_degradation(self):
        class UnpicklableError(Exception):
            def __init__(self, msg):
                super().__init__(msg)
                self.bad_attr = lambda: None  # lambdas can't be pickled

            def __reduce__(self):
                raise TypeError("cannot pickle this")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("AU2.BASE_WRITE_LOCATION", tmpdir):
                txt_path = _call_write_coredump(UnpicklableError("oops"))

            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()

            assert "Exception type:" in content

            pkl_path = Path(txt_path).with_suffix(".pkl")
            assert Path(pkl_path).is_file()

            with open(pkl_path, "rb") as f:
                loaded = pickle.load(f)

            assert isinstance(loaded, CoreDumpData)
            assert loaded.exception is None
            assert loaded.exception_type == "UnpicklableError"

    def test_fallback_when_au2_import_fails(self):
        """write_coredump should still work if AU2 constants can't be imported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import builtins
            original_import = builtins.__import__

            def failing_import(name, *args, **kwargs):
                if name == "AU2":
                    raise ImportError("simulated AU2 import failure")
                if name.startswith("AU2.database"):
                    raise ImportError("simulated database import failure")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", side_effect=failing_import):
                with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                    txt_path = _call_write_coredump(RuntimeError("import fail"))

            assert Path(txt_path).is_file()
            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "=== AU2 CRASH REPORT ===" in content
            assert "TBD" in content

            pkl_path = Path(txt_path).with_suffix(".pkl")
            with open(pkl_path, "rb") as f:
                loaded = pickle.load(f)
            assert loaded.assassins_database is None
            assert loaded.events_database is None
            assert loaded.generic_state_database is None

    def test_coredump_contains_database_fields(self):
        """Unpickled CoreDumpData should have all three database attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("AU2.BASE_WRITE_LOCATION", tmpdir):
                txt_path = _call_write_coredump(RuntimeError("db test"))

            pkl_path = Path(txt_path).with_suffix(".pkl")
            with open(pkl_path, "rb") as f:
                loaded = pickle.load(f)

            assert isinstance(loaded, CoreDumpData)
            assert hasattr(loaded, "assassins_database")
            assert hasattr(loaded, "events_database")
            assert hasattr(loaded, "generic_state_database")

    def test_coredump_data_has_environment_info(self):
        """All environment/debug fields should be non-empty strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("AU2.BASE_WRITE_LOCATION", tmpdir):
                txt_path = _call_write_coredump(RuntimeError("env test"))

            pkl_path = Path(txt_path).with_suffix(".pkl")
            with open(pkl_path, "rb") as f:
                loaded = pickle.load(f)

            assert isinstance(loaded, CoreDumpData)
            for field in [
                "au2_version",
                "python_version",
                "platform_info",
                "os_info",
                "timestamp",
                "working_directory",
                "database_location",
            ]:
                value = getattr(loaded, field)
                assert isinstance(value, str), f"{field} should be a string"
                assert len(value) > 0, f"{field} should be non-empty"
