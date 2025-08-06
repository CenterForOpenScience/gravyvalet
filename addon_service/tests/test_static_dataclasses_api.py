from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service.common.known_imps import AddonImpRegistry
from addon_toolkit.interfaces.foreign_addon_imp_config import ForeignAddonImpConfig
from addon_toolkit.interfaces.storage import StorageAddonImp


class MockForeignStorageImp(StorageAddonImp):
    """Mock foreign addon for API testing."""


class MockForeignAddonConfig(ForeignAddonImpConfig):
    """Mock foreign addon config for API testing."""

    name = "foreign_addons.mock_storage"
    path = "/fake/path"  # Add a fake path to satisfy Django's requirements

    @property
    def imp(self):
        return MockForeignStorageImp

    @property
    def addon_imp_name(self):
        return "MOCK_STORAGE"


class TestAddonImpsView(APITestCase):
    def setUp(self):
        """Set up test with clean registry."""
        self._original_name_imp_map = AddonImpRegistry._name_imp_map.copy()
        self._original_number_name_map = AddonImpRegistry._number_name_map.copy()
        AddonImpRegistry.clear()
        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[MockForeignAddonConfig("foreign_addons.mock_storage", None)],
        ):
            # Register built-in and foreign addon imps for testing
            ADDON_IMPS = {
                # Type: Storage
                "BOX": 1001,
                "S3": 1003,
                "GOOGLEDRIVE": 1005,
                "DROPBOX": 1006,
                "FIGSHARE": 1007,
                "ONEDRIVE": 1008,
                "OWNCLOUD": 1009,
                "DATAVERSE": 1010,
                "GITLAB": 1011,
                "BITBUCKET": 1012,
                "GITHUB": 1013,
                "AZUREBLOBSTORAGE": 1014,
                # Type: Citation
                "ZOTERO": 1002,
                "MENDELEY": 1004,
                # Type: Cloud Computing
                "BOA": 1020,
                # Type: Link
                "LINK_DATAVERSE": 1030,
                # Type: Redirect
                "REDIRECT_DUMMY": 1040,
                # Foreign Addon Imps
                "MOCK_STORAGE": 5001,
                # For testing
                "BLARG": -7,
            }
            AddonImpRegistry.register_addon_imps(ADDON_IMPS)

    def tearDown(self):
        """Restore original registry state after each test."""
        AddonImpRegistry.clear()
        AddonImpRegistry._name_imp_map.update(self._original_name_imp_map)
        AddonImpRegistry._number_name_map.update(self._original_number_name_map)

    def test_get(self):
        _resp = self.client.get(reverse("addon-imps-list"))
        _data = _resp.json()["data"]
        _registered_names = {
            AddonImpRegistry.get_imp_name(imp)
            for imp in AddonImpRegistry.get_all_addon_imps()
        }
        _retrieved_names = {_datum["attributes"]["name"] for _datum in _data}
        self.assertEqual(_registered_names, _retrieved_names)

    def test_unallowed_methods(self): ...


class TestAddonOperationsView(APITestCase):
    def setUp(self):
        """Set up test with clean registry."""
        self._original_name_imp_map = AddonImpRegistry._name_imp_map.copy()
        self._original_number_name_map = AddonImpRegistry._number_name_map.copy()
        AddonImpRegistry.clear()
        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[MockForeignAddonConfig("foreign_addons.mock_storage", None)],
        ):
            # Register built-in and foreign addon imps for testing
            ADDON_IMPS = {
                # Type: Storage
                "BOX": 1001,
                "S3": 1003,
                "GOOGLEDRIVE": 1005,
                "DROPBOX": 1006,
                "FIGSHARE": 1007,
                "ONEDRIVE": 1008,
                "OWNCLOUD": 1009,
                "DATAVERSE": 1010,
                "GITLAB": 1011,
                "BITBUCKET": 1012,
                "GITHUB": 1013,
                "AZUREBLOBSTORAGE": 1014,
                # Type: Citation
                "ZOTERO": 1002,
                "MENDELEY": 1004,
                # Type: Cloud Computing
                "BOA": 1020,
                # Type: Link
                "LINK_DATAVERSE": 1030,
                # Type: Redirect
                "REDIRECT_DUMMY": 1040,
                # Foreign Addon Imps
                "MOCK_STORAGE": 5001,
                # For testing
                "BLARG": -7,
            }
            AddonImpRegistry.register_addon_imps(ADDON_IMPS)

    def tearDown(self):
        """Restore original registry state after each test."""
        AddonImpRegistry.clear()
        AddonImpRegistry._name_imp_map.update(self._original_name_imp_map)
        AddonImpRegistry._number_name_map.update(self._original_number_name_map)

    def test_get(self):
        _resp = self.client.get(reverse("addon-operations-list"))
        _data = _resp.json()["data"]
        _implemented_names = {
            _op.name
            for _imp in AddonImpRegistry.get_all_addon_imps()
            for _op in _imp.all_implemented_operations()
        }
        _declared_names = {_datum["attributes"]["name"] for _datum in _data}
        self.assertEqual(_implemented_names, _declared_names)
        self.assertTrue(
            _implemented_names.issubset(_declared_names),
            f"Expected operations {_implemented_names - _declared_names} not found in API",
        )

    def test_get_with_foreign_addon_operations(self):
        """Test that foreign addon operations appear in the API response."""
        AddonImpRegistry.clear()
        AddonImpRegistry.register("MOCK_STORAGE", 5002, MockForeignStorageImp)

        _resp = self.client.get(reverse("addon-operations-list"))
        _data = _resp.json()["data"]
        _implemented_names = {
            _op.name
            for _imp in AddonImpRegistry.get_all_addon_imps()
            for _op in _imp.all_implemented_operations()
        }
        _declared_names = {_datum["attributes"]["name"] for _datum in _data}
        self.assertTrue(
            _implemented_names.issubset(_declared_names),
            f"Expected operations {_implemented_names - _declared_names} not found in API",
        )
