"""Integration tests for Foreign Addons feature."""

from unittest.mock import patch

from django.test import TestCase

from addon_service.addon_imp.models import AddonImpModel
from addon_service.common.known_imps import AddonRegistry
from addon_toolkit import AddonImp
from addon_toolkit.interfaces.citation import CitationAddonImp
from addon_toolkit.interfaces.foreign_addon_config import ForeignAddonConfig
from addon_toolkit.interfaces.storage import StorageAddonImp


# Mock Foreign Addon Implementation
class MockForeignStorageImp(StorageAddonImp):
    """Mock foreign storage addon implementation."""


class AltMockForeignStorageImp(StorageAddonImp):
    pass


class MockForeignCitationImp(CitationAddonImp):
    """Mock foreign citation addon implementation."""

    pass


class MockForeignAddonConfig(ForeignAddonConfig):
    """Mock foreign addon Django app config."""

    name = "foreign_addons.mock_storage"
    verbose_name = "Mock Foreign Addon"
    path = "/fake/path"

    @property
    def imp(self):
        """Return the AddonImp subclass."""
        return MockForeignStorageImp

    @property
    def addon_name(self):
        """Return the addon name for registration."""
        return "MOCK_STORAGE"


class AltMockForeignAddonConfig(ForeignAddonConfig):
    name = "alt_foreign_addons.alt_mock_storage"
    verbose_name = "Mock Foreign Addon Alternative"
    path = "/fake/path"

    @property
    def imp(self):
        return AltMockForeignStorageImp

    @property
    def addon_name(self):
        """Return the addon name for registration."""
        return "ALT_MOCK_STORAGE"


class MockForeignCitationAddonConfig(ForeignAddonConfig):
    name = "foreign_addons.mock_citation"
    verbose_name = "Mock Foreign Citation Addon"
    path = "/fake/path"

    @property
    def imp(self):
        return MockForeignCitationImp

    @property
    def addon_name(self):
        return "MOCK_FOREIGN_CITATION"


class TestForeignAddonDiscovery(TestCase):
    """Test foreign addon discovery and loading."""

    def setUp(self):
        """Save and Clear registry before each test."""
        self._original_name_imp_map = AddonRegistry._name_imp_map.copy()
        self._original_number_name_map = AddonRegistry._number_name_map.copy()
        AddonRegistry.clear()

    def tearDown(self):
        """Restore original registry state after each test."""
        AddonRegistry.clear()
        AddonRegistry._name_imp_map.update(self._original_name_imp_map)
        AddonRegistry._number_name_map.update(self._original_number_name_map)

    def test_foreign_addon_discovery(self):
        """Test that foreign addons are discovered from app configs."""
        mock_app_config = MockForeignAddonConfig("foreign_addons.mock_storage", None)

        addon_apps = {
            "MOCK_STORAGE": 5001,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[mock_app_config],
        ):
            AddonRegistry.register_addon_apps(addon_apps)

        self.assertEqual(
            AddonRegistry.get_imp_by_name("MOCK_STORAGE"), MockForeignStorageImp
        )
        self.assertEqual(AddonRegistry.get_imp_by_number(5001), MockForeignStorageImp)

    def test_foreign_addon_with_app_name_fallback(self):
        """Test that foreign addon can be registered using app.name if addon_name not in ADDON_APPS."""
        mock_app_config = MockForeignAddonConfig("foreign_addons.mock_storage", None)

        # Use the app's name instead of addon_name
        addon_apps = {
            "foreign_addons.mock_storage": 5001,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[mock_app_config],
        ):
            AddonRegistry.register_addon_apps(addon_apps)

        # Should be registered under the app name
        self.assertEqual(
            AddonRegistry.get_imp_by_name("foreign_addons.mock_storage"),
            MockForeignStorageImp,
        )
        self.assertEqual(AddonRegistry.get_imp_by_number(5001), MockForeignStorageImp)

    def test_multiple_foreign_addons(self):
        """Test registering multiple foreign addons."""

        addon_apps = {
            "MOCK_STORAGE": 5001,
            "ALT_MOCK_STORAGE": 5002,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[
                MockForeignAddonConfig("foreign_addons.mock_storage", None),
                AltMockForeignAddonConfig("alt_foreign_addons.alt_mock_storage", None),
            ],
        ):
            AddonRegistry.register_addon_apps(addon_apps)

        self.assertEqual(AddonRegistry.get_imp_by_number(5001), MockForeignStorageImp)
        self.assertEqual(
            AddonRegistry.get_imp_by_number(5002), AltMockForeignStorageImp
        )

    def test_mixing_foreign_and_builtin_addons(self):
        """Test that foreign and built-in addons can coexist."""
        mock_app_config = MockForeignAddonConfig("foreign_addons.mock_storage", None)

        addon_apps = {
            "BOX": 1001,  # Built-in addon
            "MOCK_STORAGE": 5001,  # Foreign addon
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[mock_app_config],
        ):
            AddonRegistry.register_addon_apps(addon_apps)

        # Both should be registered
        from addon_service.common.known_imps import KnownAddonImps

        self.assertEqual(
            AddonRegistry.get_imp_by_number(1001), KnownAddonImps.BOX.value
        )
        self.assertEqual(AddonRegistry.get_imp_by_number(5001), MockForeignStorageImp)

    @patch("addon_service.common.known_imps.logger")
    def test_foreign_addon_not_in_installed_apps(self, mock_logger):
        """Test warning when foreign addon in ADDON_APPS but not in INSTALLED_APPS."""
        addon_apps = {
            "MISSING_FOREIGN": 5001,
        }

        # No app configs returned (simulating addon not in INSTALLED_APPS)
        with patch(
            "addon_service.common.known_imps.apps.get_app_configs", return_value=[]
        ):
            AddonRegistry.register_addon_apps(addon_apps)

        mock_logger.warning.assert_called_once()
        self.assertIn(
            "No addon app has name MISSING_FOREIGN", mock_logger.warning.call_args[0][0]
        )


class TestForeignAddonInterfaceValidation(TestCase):
    """Test foreign addon interface requirements."""

    def test_foreign_addon_operations(self):
        """Test that foreign addon operations are properly exposed."""
        operations = MockForeignStorageImp.all_implemented_operations()

        self.assertEqual(len(operations), 0)


class TestForeignAddonAPIIntegration(TestCase):
    """Test that foreign addons integrate with existing API."""

    def setUp(self):
        """Set up test with registered foreign addon."""
        self._original_name_imp_map = AddonRegistry._name_imp_map.copy()
        self._original_number_name_map = AddonRegistry._number_name_map.copy()
        AddonRegistry.clear()
        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[MockForeignAddonConfig("foreign_addons.mock_storage", None)],
        ):
            # Register built-in addons and a foreign addon for testing
            test_addon_apps = {
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
                # Type: Citation
                "ZOTERO": 1002,
                "MENDELEY": 1004,
                # Type: Cloud Computing
                "BOA": 1020,
                # Type: Link
                "LINK_DATAVERSE": 1030,
                # Foreign Addons
                "MOCK_STORAGE": 5001,
                # For testing
                "BLARG": -7,
            }
            AddonRegistry.register_addon_apps(test_addon_apps)

    def tearDown(self):
        """Restore original registry state after each test."""
        AddonRegistry.clear()
        AddonRegistry._name_imp_map.update(self._original_name_imp_map)
        AddonRegistry._number_name_map.update(self._original_number_name_map)

    def test_foreign_addon_in_addon_imp_model(self):
        """Test that foreign addons appear in AddonImpModel.iter_all()."""
        all_imps = list(AddonImpModel.iter_all())

        # Should include our mock foreign addon
        imp_classes = [imp.imp_cls for imp in all_imps]
        self.assertIn(MockForeignStorageImp, imp_classes)

    def test_foreign_addon_imp_model_properties(self):
        """Test that AddonImpModel works correctly with foreign addons."""
        imp_model = AddonImpModel(MockForeignStorageImp)

        self.assertEqual(imp_model.name, "MOCK_STORAGE")
        self.assertEqual(imp_model.static_key, "MOCK_STORAGE")
        self.assertEqual(imp_model.imp_cls, MockForeignStorageImp)

    def test_foreign_addon_operations_in_model(self):
        """Test that foreign addon operations are accessible through AddonImpModel."""
        imp_model = AddonImpModel(MockForeignStorageImp)
        operations = imp_model.implemented_operations

        # Should have no operations for our mock implementation
        self.assertEqual(len(operations), 0)

    def test_foreign_addon_init_from_static_key(self):
        """Test that AddonImpModel can be initialized from foreign addon name."""
        imp_model = AddonImpModel.init_args_from_static_key("MOCK_STORAGE")
        self.assertEqual(imp_model, (MockForeignStorageImp,))

    def test_foreign_addon_serialization_compatibility(self):
        """Test that foreign addons work with existing serializers."""
        from rest_framework.test import APIRequestFactory

        from addon_service.addon_imp.serializers import AddonImpSerializer

        imp_model = AddonImpModel(MockForeignStorageImp)

        # Create a mock request for the serializer context
        factory = APIRequestFactory()
        request = factory.get("/api/addon-imps/")

        serializer = AddonImpSerializer(imp_model, context={"request": request})

        data = serializer.data
        self.assertEqual(data["name"], "MOCK_STORAGE")
        self.assertIn("docstring", data)
        self.assertIn("interface_docstring", data)


class TestForeignAddonRegistryPersistence(TestCase):
    """Test that foreign addon registration persists correctly."""

    def test_registry_state_after_multiple_registrations(self):
        """Test registry state remains consistent after multiple operations."""
        AddonRegistry.clear()

        AddonRegistry.register("MOCK_STORAGE", 5001, MockForeignStorageImp)
        AddonRegistry.register("ALT_MOCK_STORAGE", 5002, AltMockForeignStorageImp)

        # Clear and re-register with different config
        AddonRegistry.clear()
        addon_apps = {
            "MOCK_FOREIGN_CITATION": 5003,
        }
        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[
                MockForeignCitationAddonConfig("foreign_addons.mock_citation", None),
            ],
        ):
            AddonRegistry.register_addon_apps(addon_apps)

        self.assertEqual(len(list(AddonRegistry.get_all_addon_imps())), 1)
        self.assertEqual(AddonRegistry.get_imp_by_number(5003), MockForeignCitationImp)

        with self.assertRaises(KeyError):
            AddonRegistry.get_imp_by_number(5001)

    def test_foreign_addon_type_filtering(self):
        """Test that foreign addons are correctly filtered by type."""
        AddonRegistry.clear()

        addon_apps = {
            "MOCK_STORAGE": 5001,
            "ALT_MOCK_STORAGE": 5002,
            "MOCK_FOREIGN_CITATION": 5003,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[
                MockForeignAddonConfig("foreign_addons.mock_storage", None),
                AltMockForeignAddonConfig("alt_foreign_addons.alt_mock_storage", None),
                MockForeignCitationAddonConfig("foreign_addons.mock_citation", None),
            ],
        ):
            AddonRegistry.register_addon_apps(addon_apps)

        # Filter by storage type
        storage_addons = list(AddonRegistry.iter_by_type(StorageAddonImp))
        self.assertEqual(len(storage_addons), 2)
        self.assertEqual(storage_addons[0], (5001, "MOCK_STORAGE"))
        self.assertEqual(storage_addons[1], (5002, "ALT_MOCK_STORAGE"))

        # Filter by citation type
        citation_addons = list(AddonRegistry.iter_by_type(CitationAddonImp))
        self.assertEqual(len(citation_addons), 1)
        self.assertEqual(citation_addons[0], (5003, "MOCK_FOREIGN_CITATION"))

        # Filter Nothing
        all_addons = list(AddonRegistry.iter_by_type(AddonImp))
        self.assertEqual(len(all_addons), 3)
        self.assertEqual(all_addons[0], (5001, "MOCK_STORAGE"))
        self.assertEqual(all_addons[1], (5002, "ALT_MOCK_STORAGE"))
        self.assertEqual(all_addons[2], (5003, "MOCK_FOREIGN_CITATION"))
