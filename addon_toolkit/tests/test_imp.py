import dataclasses
import unittest
from http import HTTPMethod

from addon_toolkit import (
    AddonCapabilities,
    AddonImp,
    AddonOperationDeclaration,
    AddonOperationType,
    BaseAddonInterface,
    RedirectResult,
    exceptions,
    immediate_operation,
    redirect_operation,
)


class TestAddonImp(unittest.TestCase):
    # the basics of an addon imp

    ###
    # shared test env (on `self`)
    _MyInterface: type[
        BaseAddonInterface
    ]  # BaseAddonInterface with operation declarations
    _MyImp: type[AddonImp]  # concrete AddonImp subclass
    _expected_get_op: AddonOperationDeclaration
    _expected_put_op: AddonOperationDeclaration
    _expected_query_op: AddonOperationDeclaration

    @classmethod
    def setUpClass(cls) -> None:
        ###
        # declare the capabilities and protocol for a category of addons

        @dataclasses.dataclass
        class _MyCustomOperationResult:
            url: str
            flibbly: int

        class _MyInterface(BaseAddonInterface):
            """this _MyInterface docstring should find its way to browsable docs somewhere"""

            @redirect_operation(capability=AddonCapabilities.ACCESS)
            def url_for_get(self, checksum_iri: str) -> RedirectResult:
                """this url_for_get docstring should find its way to docs"""
                raise exceptions.OperationNotImplemented

            @immediate_operation(capability=AddonCapabilities.ACCESS)
            async def query_relations(
                self,
                checksum_iri: str,
                query: str | None = None,
            ) -> _MyCustomOperationResult:
                """this query_relations docstring should find its way to docs"""
                raise exceptions.OperationNotImplemented

            @redirect_operation(capability=AddonCapabilities.UPDATE)
            def url_for_put(self, checksum_iri: str) -> RedirectResult:
                """this url_for_put docstring should find its way to docs"""
                raise exceptions.OperationNotImplemented

        ###
        # implement (some of) the protocol's declared operations

        class _MyImp(AddonImp):
            ADDON_INTERFACE = _MyInterface

            def url_for_get(self, checksum_iri: str) -> RedirectResult:
                """this url_for_get docstring could contain implementation-specific caveats"""
                return RedirectResult(
                    f"https://myarchive.example///{checksum_iri}",
                    HTTPMethod.GET,
                )

            def url_for_put(self, checksum_iri: str) -> RedirectResult:
                """this url_for_put docstring could contain implementation-specific caveats"""
                return RedirectResult(
                    f"https://myarchive.example///{checksum_iri}",
                    HTTPMethod.PUT,
                )

        # shared static types
        cls._MyInterface = _MyInterface
        cls._MyImp = _MyImp

        # shared operations
        cls._expected_get_op = AddonOperationDeclaration(
            operation_type=AddonOperationType.REDIRECT,
            capability=AddonCapabilities.ACCESS,
            operation_fn=_MyInterface.url_for_get,
        )
        cls._expected_put_op = AddonOperationDeclaration(
            operation_type=AddonOperationType.REDIRECT,
            capability=AddonCapabilities.UPDATE,
            operation_fn=_MyInterface.url_for_put,
        )
        cls._expected_query_op = AddonOperationDeclaration(
            operation_type=AddonOperationType.IMMEDIATE,
            capability=AddonCapabilities.ACCESS,
            operation_fn=_MyInterface.query_relations,
        )

    def test_iter_declared_operations(self) -> None:
        self.assertEqual(
            set(self._MyInterface.iter_declared_operations()),
            {self._expected_get_op, self._expected_put_op, self._expected_query_op},
        )

    def test_all_implemented_operations(self) -> None:
        _all = self._MyImp.all_implemented_operations()
        self.assertIsInstance(_all, frozenset)
        self.assertEqual(
            _all,
            {self._expected_get_op, self._expected_put_op},
        )

    def test_implemented_operations(self) -> None:
        for _capabilities, _expected in (
            (
                AddonCapabilities.ACCESS,
                {self._expected_get_op},
            ),
            (AddonCapabilities.UPDATE, {self._expected_put_op}),
            (
                AddonCapabilities.ACCESS | AddonCapabilities.UPDATE,
                {self._expected_get_op, self._expected_put_op},
            ),
        ):
            self.assertEqual(
                set(self._MyImp.implemented_operations_for_capabilities(_capabilities)),
                _expected,
            )

    def test_operation_by_name(self) -> None:
        self.assertEqual(
            self._MyImp.get_operation_declaration("url_for_get"),
            self._expected_get_op,
        )
        self.assertEqual(
            self._MyImp.get_operation_declaration("url_for_put"),
            self._expected_put_op,
        )

    def test_invoke_operation(self) -> None:
        _myimp_instance = self._MyImp()
        _result = _myimp_instance.invoke_operation__blocking(
            self._MyImp.get_operation_declaration("url_for_get"),
            {"checksum_iri": "..."},
        )
        self.assertEqual(
            _result,
            RedirectResult(
                "https://myarchive.example///...",
                HTTPMethod.GET,
            ),
        )
