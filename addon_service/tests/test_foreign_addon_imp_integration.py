"""Integration tests for Foreign Addon Imps feature."""

from unittest.mock import patch

from django.test import TestCase

from addon_service.addon_imp.models import AddonImpModel
from addon_service.common.known_imps import AddonImpRegistry
from addon_toolkit import AddonImp
from addon_toolkit.interfaces.citation import CitationAddonImp
from addon_toolkit.interfaces.foreign_addon_imp_config import ForeignAddonImpConfig
from addon_toolkit.interfaces.storage import StorageAddonImp


# Mock Foreign Addon Imp Implementation
class MockForeignStorageImp(StorageAddonImp):
    """Mock foreign storage addon imp implementation."""


class AltMockForeignStorageImp(StorageAddonImp):
    pass


class MockForeignCitationImp(CitationAddonImp):
    """Mock foreign citation addon imp implementation."""

    pass


class MockForeignAddonImpConfig(ForeignAddonImpConfig):
    """Mock foreign addon imp Django app config."""

    name = "foreign_addon_imps.mock_storage"
    verbose_name = "Mock Foreign Addon Imp"
    path = "/fake/path"

    @property
    def imp(self):
        """Return the AddonImp subclass."""
        return MockForeignStorageImp

    @property
    def addon_imp_name(self):
        """Return the addon imp name for registration."""
        return "MOCK_STORAGE"


class AltMockForeignAddonImpConfig(ForeignAddonImpConfig):
    name = "alt_foreign_addon_imps.alt_mock_storage"
    verbose_name = "Mock Foreign Addon Imp Alternative"
    path = "/fake/path"

    @property
    def imp(self):
        return AltMockForeignStorageImp

    @property
    def addon_imp_name(self):
        """Return the addon imp name for registration."""
        return "ALT_MOCK_STORAGE"


class MockForeignCitationAddonImpConfig(ForeignAddonImpConfig):
    name = "foreign_addon_imps.mock_citation"
    verbose_name = "Mock Foreign Citation Addon Imp"
    path = "/fake/path"

    @property
    def imp(self):
        return MockForeignCitationImp

    @property
    def addon_imp_name(self):
        return "MOCK_FOREIGN_CITATION"


class TestForeignAddonImpDiscovery(TestCase):
    """Test foreign addon imp discovery and loading."""

    def setUp(self):
        """Save and Clear registry before each test."""
        self._original_name_imp_map = AddonImpRegistry._name_imp_map.copy()
        self._original_number_name_map = AddonImpRegistry._number_name_map.copy()
        AddonImpRegistry.clear()

    def tearDown(self):
        """Restore original registry state after each test."""
        AddonImpRegistry.clear()
        AddonImpRegistry._name_imp_map.update(self._original_name_imp_map)
        AddonImpRegistry._number_name_map.update(self._original_number_name_map)

    def test_foreign_addon_imp_discovery(self):
        """Test that foreign addon imps are discovered from app configs."""
        mock_app_config = MockForeignAddonImpConfig(
            "foreign_addon_imps.mock_storage", None
        )

        ADDON_IMPS = {
            "MOCK_STORAGE": 5001,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[mock_app_config],
        ):
            AddonImpRegistry.register_addon_imps(ADDON_IMPS)

        self.assertEqual(
            AddonImpRegistry.get_imp_by_name("MOCK_STORAGE"), MockForeignStorageImp
        )
        self.assertEqual(
            AddonImpRegistry.get_imp_by_number(5001), MockForeignStorageImp
        )

    def test_foreign_addon_imp_with_app_name_fallback(self):
        """Test that foreign addon imp can be registered using app.name if addon_imp_name is not in ADDON_IMPS."""
        mock_app_config = MockForeignAddonImpConfig(
            "foreign_addon_imps.mock_storage", None
        )

        # Use the app's name instead of addon_imp_name
        ADDON_IMPS = {
            "foreign_addon_imps.mock_storage": 5001,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[mock_app_config],
        ):
            AddonImpRegistry.register_addon_imps(ADDON_IMPS)

        # Should be registered under the app name
        self.assertEqual(
            AddonImpRegistry.get_imp_by_name("foreign_addon_imps.mock_storage"),
            MockForeignStorageImp,
        )
        self.assertEqual(
            AddonImpRegistry.get_imp_by_number(5001), MockForeignStorageImp
        )

    def test_multiple_foreign_addon_imps(self):
        """Test registering multiple foreign addon imps."""

        ADDON_IMPS = {
            "MOCK_STORAGE": 5001,
            "ALT_MOCK_STORAGE": 5002,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[
                MockForeignAddonImpConfig("foreign_addon_imps.mock_storage", None),
                AltMockForeignAddonImpConfig(
                    "alt_foreign_addon_imps.alt_mock_storage", None
                ),
            ],
        ):
            AddonImpRegistry.register_addon_imps(ADDON_IMPS)

        self.assertEqual(
            AddonImpRegistry.get_imp_by_number(5001), MockForeignStorageImp
        )
        self.assertEqual(
            AddonImpRegistry.get_imp_by_number(5002), AltMockForeignStorageImp
        )

    def test_mixing_foreign_and_builtin_addon_imps(self):
        """Test that foreign and built-in addon imps can coexist."""
        mock_app_config = MockForeignAddonImpConfig(
            "foreign_addon_imps.mock_storage", None
        )

        ADDON_IMPS = {
            "BOX": 1001,  # Built-in addon
            "MOCK_STORAGE": 5001,  # Foreign addon imp
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[mock_app_config],
        ):
            AddonImpRegistry.register_addon_imps(ADDON_IMPS)

        # Both should be registered
        from addon_service.common.known_imps import KnownAddonImps

        self.assertEqual(
            AddonImpRegistry.get_imp_by_number(1001), KnownAddonImps.BOX.value
        )
        self.assertEqual(
            AddonImpRegistry.get_imp_by_number(5001), MockForeignStorageImp
        )

    @patch("addon_service.common.known_imps.logger")
    def test_foreign_addon_imp_not_in_installed_apps(self, mock_logger):
        """Test warning when foreign addon imp in ADDON_IMPS but not in INSTALLED_APPS."""
        ADDON_IMPS = {
            "MISSING_FOREIGN": 5001,
        }

        # No app configs returned (simulating addon imp app not in INSTALLED_APPS)
        with patch(
            "addon_service.common.known_imps.apps.get_app_configs", return_value=[]
        ):
            AddonImpRegistry.register_addon_imps(ADDON_IMPS)

        mock_logger.warning.assert_called_once()
        self.assertIn(
            "No addon imp has name MISSING_FOREIGN", mock_logger.warning.call_args[0][0]
        )


class TestForeignAddonImpInterfaceValidation(TestCase):
    """Test foreign addon imp interface requirements."""

    def test_foreign_addon_imp_operations(self):
        """Test that foreign addon imp operations are properly exposed."""
        operations = MockForeignStorageImp.all_implemented_operations()

        self.assertEqual(len(operations), 0)


class TestForeignAddonImpAPIIntegration(TestCase):
    """Test that foreign addon imps integrate with existing API."""

    def setUp(self):
        """Set up test with registered foreign addon imps."""
        self._original_name_imp_map = AddonImpRegistry._name_imp_map.copy()
        self._original_number_name_map = AddonImpRegistry._number_name_map.copy()
        AddonImpRegistry.clear()
        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[
                MockForeignAddonImpConfig("foreign_addon_imps.mock_storage", None)
            ],
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

    def test_foreign_addon_imp_in_addon_imp_model(self):
        """Test that foreign addon imps appear in AddonImpModel.iter_all()."""
        all_imps = list(AddonImpModel.iter_all())

        # Should include our mock foreign addon imp
        imp_classes = [imp.imp_cls for imp in all_imps]
        self.assertIn(MockForeignStorageImp, imp_classes)

    def test_foreign_addon_imp_model_properties(self):
        """Test that AddonImpModel works correctly with foreign addon imps."""
        imp_model = AddonImpModel(MockForeignStorageImp)

        self.assertEqual(imp_model.name, "MOCK_STORAGE")
        self.assertEqual(imp_model.static_key, "MOCK_STORAGE")
        self.assertEqual(imp_model.imp_cls, MockForeignStorageImp)

    def test_foreign_addon_imp_operations_in_model(self):
        """Test that foreign addon imp operations are accessible through AddonImpModel."""
        imp_model = AddonImpModel(MockForeignStorageImp)
        operations = imp_model.implemented_operations

        # Should have no operations for our mock implementation
        self.assertEqual(len(operations), 0)

    def test_foreign_addon_imp_init_from_static_key(self):
        """Test that AddonImpModel can be initialized from foreign addon imp name."""
        imp_model = AddonImpModel.init_args_from_static_key("MOCK_STORAGE")
        self.assertEqual(imp_model, (MockForeignStorageImp,))

    def test_foreign_addon_imp_serialization_compatibility(self):
        """Test that foreign addon imps work with existing serializers."""
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


class TestForeignAddonImpRegistryPersistence(TestCase):
    """Test that foreign addon imp registration persists correctly."""

    def test_registry_state_after_multiple_registrations(self):
        """Test registry state remains consistent after multiple operations."""
        AddonImpRegistry.clear()

        AddonImpRegistry.register("MOCK_STORAGE", 5001, MockForeignStorageImp)
        AddonImpRegistry.register("ALT_MOCK_STORAGE", 5002, AltMockForeignStorageImp)

        # Clear and re-register with different config
        AddonImpRegistry.clear()
        ADDON_IMPS = {
            "MOCK_FOREIGN_CITATION": 5003,
        }
        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[
                MockForeignCitationAddonImpConfig(
                    "foreign_addon_imps.mock_citation", None
                ),
            ],
        ):
            AddonImpRegistry.register_addon_imps(ADDON_IMPS)

        self.assertEqual(len(list(AddonImpRegistry.get_all_addon_imps())), 1)
        self.assertEqual(
            AddonImpRegistry.get_imp_by_number(5003), MockForeignCitationImp
        )

        with self.assertRaises(KeyError):
            AddonImpRegistry.get_imp_by_number(5001)

    def test_foreign_addon_imp_type_filtering(self):
        """Test that foreign addon imps are correctly filtered by type."""
        AddonImpRegistry.clear()

        ADDON_IMPS = {
            "MOCK_STORAGE": 5001,
            "ALT_MOCK_STORAGE": 5002,
            "MOCK_FOREIGN_CITATION": 5003,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs",
            return_value=[
                MockForeignAddonImpConfig("foreign_addon_imps.mock_storage", None),
                AltMockForeignAddonImpConfig(
                    "alt_foreign_addon_imps.alt_mock_storage", None
                ),
                MockForeignCitationAddonImpConfig(
                    "foreign_addon_imps.mock_citation", None
                ),
            ],
        ):
            AddonImpRegistry.register_addon_imps(ADDON_IMPS)

        # Filter by storage type
        storage_addons = list(AddonImpRegistry.iter_by_type(StorageAddonImp))
        self.assertEqual(len(storage_addons), 2)
        self.assertEqual(storage_addons[0], (5001, "MOCK_STORAGE"))
        self.assertEqual(storage_addons[1], (5002, "ALT_MOCK_STORAGE"))

        # Filter by citation type
        citation_addons = list(AddonImpRegistry.iter_by_type(CitationAddonImp))
        self.assertEqual(len(citation_addons), 1)
        self.assertEqual(citation_addons[0], (5003, "MOCK_FOREIGN_CITATION"))

        # Filter Nothing
        all_addons = list(AddonImpRegistry.iter_by_type(AddonImp))
        self.assertEqual(len(all_addons), 3)
        self.assertEqual(all_addons[0], (5001, "MOCK_STORAGE"))
        self.assertEqual(all_addons[1], (5002, "ALT_MOCK_STORAGE"))
        self.assertEqual(all_addons[2], (5003, "MOCK_FOREIGN_CITATION"))
