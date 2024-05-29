import doctest


def load_doctests(*modules):
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

    def _load_tests(loader, tests, pattern):
        for _module in modules:
            tests.addTests(
                doctest.DocTestSuite(
                    _module,
                    optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE,
                )
            )
        return tests

    return _load_tests
