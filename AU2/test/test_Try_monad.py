import unittest
from AU2.plugins.util.types import Try, Success, Failure

class CustomException(Exception):
    """Custom exception type to give as a failure value for testing"""

class CustomException2(Exception):
    """
    Another custom exception type to give as a failure value for testing, that needs to be distinct from CustomException
    """

class TestTryMonad(unittest.TestCase):
    def __init__(self, *args):
        self.t = Success("test string")
        self.f = Failure(CustomException("Generic error"))
        super().__init__(*args)

    def test_Success_get_or_else(self):
        self.assertEqual(self.t.get_or_else(lambda _: "error output"), "test string")

    def test_Failure_get_or_else(self):
        self.assertEqual(self.f.get_or_else(lambda err: err.args[0]), "Generic error")

    def test_map_no_error(self):
        t_after_map = self.t.map(lambda value: value + " with more")
        self.assertTrue(isinstance(t_after_map, Success))
        self.assertEqual(t_after_map.get_or_else(lambda _: "error output"), "test string with more")

        f_after_map = self.f.map(lambda value: value + " with more")
        self.assertEqual(f_after_map.get_or_else(lambda err: err.args[0]), "Generic error")

    def test_map_with_error(self):
        t_after_map = self.t.map(lambda value: value + 289238)
        self.assertTrue(isinstance(t_after_map, Failure))
        self.assertEqual(t_after_map.get_or_else(
            lambda err: "tried to add int to str" if isinstance(err, TypeError) else "other error"),
        "tried to add int to str")

        f_after_map = self.f.map(lambda value: value + 289238)
        self.assertEqual(f_after_map.get_or_else(
            lambda err: "tried to add int to str" if isinstance(err, TypeError) else "other error"),
        "other error")

    def raise_(self, err):
        raise err

    def test_map_failure(self):
        self.t.map_failure(lambda _: self.raise_(AssertionError("This code should be unreachable.")))
        self.assertRaises(CustomException2, lambda: self.f.map_failure(lambda err: self.raise_(CustomException2("Some exception"))))

    def test_or_throw(self):
        self.t.or_throw(lambda _: AssertionError("This code should be unreachable."))
        self.assertRaises(CustomException, lambda: self.f.or_throw(lambda err: self.raise_(err)))


if __name__ == '__main__':
    unittest.main()
