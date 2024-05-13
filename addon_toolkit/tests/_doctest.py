import doctest
import typing
import unittest
from types import ModuleType


class LoadTestsFunction(typing.Protocol):
    """structural type for the function expected by the "load_tests protocol"
    https://docs.python.org/3/library/unittest.html#load-tests-protocol
    """

    def __call__(
        _,  # implicit, nonexistent "self"
        loader: unittest.TestLoader,
        tests: unittest.TestSuite,
        pattern: str | None,
    ) -> unittest.TestSuite: ...


def load_doctests(
    *modules: ModuleType,
    doctestflags: int = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE,
) -> LoadTestsFunction:
    """shorthand for unittests from doctests

    meant for implementing the "load_tests protocol"
    https://docs.python.org/3/library/unittest.html#load-tests-protocol

    suggested use, in a separate file from `unittest` unit tests
    ```
    from addon_toolkit.tests._doctest import load_doctests
    import my.module.with.doctests

    load_tests = load_doctests(my.module.with.doctests)
    ```

    (if there's a need, could support pass-thru kwargs to DocTestSuite)
    """

    def _load_tests(
        loader: unittest.TestLoader,
        tests: unittest.TestSuite,
        pattern: str | None,
    ) -> unittest.TestSuite:
        for _module in modules:
            tests.addTests(
                doctest.DocTestSuite(
                    _module,
                    optionflags=doctestflags,
                )
            )
        return tests

    return _load_tests
