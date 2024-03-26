import dataclasses
import enum
import typing
import unittest
from http import HTTPMethod
from unittest.mock import Mock

from addon_toolkit import (
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
    class _MyCapability(enum.Enum):
        GET_IT = "get-it"
        PUT_IT = "put-it"
        UNUSED = "unused"  # for testing when a capability has no operations

    ###
    # shared test env (on `self`)
    _MyProtocol: type  # typing.Protocol subclass decorated with `@addon_protocol`
    _MyImplementation: type  # subclass of _MyProtocol
    _my_imp: AddonImp
    _expected_get_op: AddonOperationDeclaration
    _expected_put_op: AddonOperationDeclaration
    _expected_query_op: AddonOperationDeclaration
    _expected_get_imp: AddonOperationImp
    _expected_put_imp: AddonOperationImp

    @classmethod
    def setUpClass(cls):
        ###
        # declare the capabilities and protocol for a category of addons

        @dataclasses.dataclass
        class _MyCustomOperationResult:
            url: str
            flibbly: int

        @addon_protocol()
        class _MyProtocol(typing.Protocol):
            """this _MyProtocol docstring should find its way to browsable docs somewhere"""

            @redirect_operation(capability=cls._MyCapability.GET_IT)
            def url_for_get(self, checksum_iri) -> RedirectResult:
                """this url_for_get docstring should find its way to docs"""
                ...

            @immediate_operation(capability=cls._MyCapability.GET_IT)
            async def query_relations(
                self, checksum_iri, query=None
            ) -> _MyCustomOperationResult:
                """this query_relations docstring should find its way to docs"""
                ...

            @redirect_operation(capability=cls._MyCapability.PUT_IT)
            def url_for_put(self, checksum_iri) -> RedirectResult:
                """this url_for_put docstring should find its way to docs"""
                ...

        ###
        # implement (some of) the protocol's declared operations

        class _MyImplementation(_MyProtocol):
            def url_for_get(self, checksum_iri) -> RedirectResult:
                """this url_for_get docstring could contain implementation-specific caveats"""
                return RedirectResult(
                    HTTPMethod.GET,
                    f"https://myarchive.example///{checksum_iri}",
                )

            def url_for_put(self, checksum_iri) -> RedirectResult:
                """this url_for_put docstring could contain implementation-specific caveats"""
                return RedirectResult(
                    HTTPMethod.PUT,
                    f"https://myarchive.example///{checksum_iri}",
                )

        # shared static types
        cls._MyProtocol = _MyProtocol
        cls._MyImplementation = _MyImplementation

        # shared operations
        cls._expected_get_op = AddonOperationDeclaration(
            operation_type=AddonOperationType.REDIRECT,
            capability=cls._MyCapability.GET_IT,
            operation_fn=_MyProtocol.url_for_get,
        )
        cls._expected_put_op = AddonOperationDeclaration(
            operation_type=AddonOperationType.REDIRECT,
            capability=cls._MyCapability.PUT_IT,
            operation_fn=_MyProtocol.url_for_put,
        )
        cls._expected_query_op = AddonOperationDeclaration(
            operation_type=AddonOperationType.IMMEDIATE,
            capability=cls._MyCapability.GET_IT,
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
            operation=cls._expected_get_op,
        )
        cls._expected_put_imp = AddonOperationImp(
            addon_imp=cls._my_imp,
            operation=cls._expected_put_op,
        )

    def test_get_operations(self):
        _protocol_dec = addon_protocol.get_declaration(self._MyProtocol)
        self.assertEqual(
            set(_protocol_dec.get_operation_declarations()),
            {self._expected_get_op, self._expected_put_op, self._expected_query_op},
        )
        self.assertEqual(
            set(
                _protocol_dec.get_operation_declarations(
                    capabilities=[self._MyCapability.GET_IT]
                )
            ),
            {self._expected_get_op, self._expected_query_op},
        )
        self.assertEqual(
            set(
                _protocol_dec.get_operation_declarations(
                    capabilities=[self._MyCapability.PUT_IT]
                )
            ),
            {self._expected_put_op},
        )
        self.assertEqual(
            set(
                _protocol_dec.get_operation_declarations(
                    capabilities=[self._MyCapability.UNUSED]
                )
            ),
            set(),
        )

    def test_get_operation_imps(self):
        self.assertEqual(
            set(self._my_imp.get_operation_imps()),
            {self._expected_get_imp, self._expected_put_imp},
        )
        self.assertEqual(
            set(
                self._my_imp.get_operation_imps(
                    capabilities=[self._MyCapability.GET_IT]
                )
            ),
            {self._expected_get_imp},
        )
        self.assertEqual(
            set(
                self._my_imp.get_operation_imps(
                    capabilities=[self._MyCapability.PUT_IT]
                )
            ),
            {self._expected_put_imp},
        )
        self.assertEqual(
            set(
                self._my_imp.get_operation_imps(
                    capabilities=[self._MyCapability.UNUSED]
                )
            ),
            set(),
        )

    def test_operation_imp_by_name(self):
        self.assertEqual(
            self._my_imp.get_operation_imp_by_name("url_for_get"),
            self._expected_get_imp,
        )
        self.assertEqual(
            self._my_imp.get_operation_imp_by_name("url_for_put"),
            self._expected_put_imp,
        )

    def test_operation_call(self):
        _mock_addon_instance = Mock()
        _imp_for_get = self._my_imp.get_operation_imp_by_name("url_for_get")
        _imp_for_get.call_with_json_kwargs(
            _mock_addon_instance,
            {"checksum_iri": "..."},
        )
        _mock_addon_instance.assert_called_once_with(checksum_iri="...")
