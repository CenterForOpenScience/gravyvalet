import dataclasses
import typing
import unittest
from http import HTTPMethod
from unittest.mock import Mock

from addon_toolkit import (
    AddonCapabilities,
    AddonImp,
    AddonOperationDeclaration,
    AddonOperationImp,
    RedirectResult,
    addon_protocol,
    immediate_operation,
    redirect_operation,
)
from addon_toolkit.operation import AddonOperationType


class TestAddonProtocol(unittest.TestCase):
    # the basics of an addon protocol

    ###
    # shared test env (initialized by setUpClass)
    _MyProtocol: type  # typing.Protocol subclass decorated with `@addon_protocol`
    _MyImplementation: type  # subclass of _MyProtocol
    _my_imp: AddonImp
    _expected_get_op: AddonOperationDeclaration
    _expected_put_op: AddonOperationDeclaration
    _expected_query_op: AddonOperationDeclaration
    _expected_get_imp: AddonOperationImp
    _expected_put_imp: AddonOperationImp

    @classmethod
    def setUpClass(cls) -> None:
        ###
        # declare the capabilities and protocol for a category of addons

        @dataclasses.dataclass
        class _MyCustomOperationResult:
            url: str
            flibbly: int

        @addon_protocol()
        class _MyProtocol(typing.Protocol):
            """this _MyProtocol docstring should find its way to browsable docs somewhere"""

            @redirect_operation(capability=AddonCapabilities.ACCESS)
            def url_for_get(self, checksum_iri: str) -> RedirectResult:
                """this url_for_get docstring should find its way to docs"""
                ...

            @immediate_operation(capability=AddonCapabilities.ACCESS)
            async def query_relations(
                self,
                checksum_iri: str,
                query: str | None = None,
            ) -> _MyCustomOperationResult:
                """this query_relations docstring should find its way to docs"""
                ...

            @redirect_operation(capability=AddonCapabilities.UPDATE)
            def url_for_put(self, checksum_iri: str) -> RedirectResult:
                """this url_for_put docstring should find its way to docs"""
                ...

        ###
        # implement (some of) the protocol's declared operations

        class _MyImplementation(_MyProtocol):
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
        cls._MyProtocol = _MyProtocol
        cls._MyImplementation = _MyImplementation

        # shared operations
        cls._expected_get_op = AddonOperationDeclaration(
            operation_type=AddonOperationType.REDIRECT,
            capability=AddonCapabilities.ACCESS,
            operation_fn=_MyProtocol.url_for_get,
        )
        cls._expected_put_op = AddonOperationDeclaration(
            operation_type=AddonOperationType.REDIRECT,
            capability=AddonCapabilities.UPDATE,
            operation_fn=_MyProtocol.url_for_put,
        )
        cls._expected_query_op = AddonOperationDeclaration(
            operation_type=AddonOperationType.IMMEDIATE,
            capability=AddonCapabilities.ACCESS,
            operation_fn=_MyProtocol.query_relations,
        )
        cls._my_imp = AddonImp(
            _MyProtocol,
            imp_cls=_MyImplementation,
            imp_number=7,
        )

        # a specific implementation of some of those shared operations
        cls._expected_get_imp = AddonOperationImp(
            addon_imp=cls._my_imp,
            declaration=cls._expected_get_op,
        )
        cls._expected_put_imp = AddonOperationImp(
            addon_imp=cls._my_imp,
            declaration=cls._expected_put_op,
        )

    def test_get_operations(self) -> None:
        _protocol_dec = addon_protocol.get_declaration(self._MyProtocol)
        self.assertEqual(
            set(_protocol_dec.get_operation_declarations()),
            {self._expected_get_op, self._expected_put_op, self._expected_query_op},
        )
        self.assertEqual(
            set(
                _protocol_dec.get_operation_declarations(
                    capabilities=[AddonCapabilities.ACCESS]
                )
            ),
            {self._expected_get_op, self._expected_query_op},
        )
        self.assertEqual(
            set(
                _protocol_dec.get_operation_declarations(
                    capabilities=[AddonCapabilities.UPDATE]
                )
            ),
            {self._expected_put_op},
        )

    def test_get_operation_imps(self) -> None:
        self.assertEqual(
            set(self._my_imp.get_operation_imps()),
            {self._expected_get_imp, self._expected_put_imp},
        )
        self.assertEqual(
            set(
                self._my_imp.get_operation_imps(capabilities=[AddonCapabilities.ACCESS])
            ),
            {self._expected_get_imp},
        )
        self.assertEqual(
            set(
                self._my_imp.get_operation_imps(capabilities=[AddonCapabilities.UPDATE])
            ),
            {self._expected_put_imp},
        )

    def test_operation_imp_by_name(self) -> None:
        self.assertEqual(
            self._my_imp.get_operation_imp_by_name("url_for_get"),
            self._expected_get_imp,
        )
        self.assertEqual(
            self._my_imp.get_operation_imp_by_name("url_for_put"),
            self._expected_put_imp,
        )

    def test_operation_call(self) -> None:
        _mock_addon_instance = Mock()
        _mock_addon_instance.url_for_get.return_value = RedirectResult(
            "https://myarchive.example///...",
            HTTPMethod.GET,
        )
        _imp_for_get = self._my_imp.get_operation_imp_by_name("url_for_get")
        _imp_for_get.invoke_thru_addon__blocking(
            _mock_addon_instance,
            {"checksum_iri": "..."},
        )
        _mock_addon_instance.url_for_get.assert_called_once_with(checksum_iri="...")
