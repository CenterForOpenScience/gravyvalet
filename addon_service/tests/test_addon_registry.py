"""Tests for the AddonRegistry class."""

from unittest.mock import patch

from django.test import TestCase

from addon_service.common.known_imps import (
    AddonRegistry,
    KnownAddonImps,
)
from addon_toolkit import AddonImp
from addon_toolkit.interfaces.citation import CitationAddonImp
from addon_toolkit.interfaces.storage import StorageAddonImp


class MockStorageImp(StorageAddonImp):
    """Mock storage addon for testing."""


class MockCitationImp(CitationAddonImp):
    """Mock citation addon for testing."""


class TestAddonRegistry(TestCase):
    """Test cases for AddonRegistry class."""

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

    # Test 1: Registration Mechanics
    def test_register_addon_success(self):
        """Test successful registration of an addon."""
        AddonRegistry.register("TEST_ADDON", 9999, MockStorageImp)

        self.assertEqual(AddonRegistry.get_imp_by_name("TEST_ADDON"), MockStorageImp)
        self.assertEqual(AddonRegistry.get_name_by_number(9999), "TEST_ADDON")
        self.assertEqual(AddonRegistry.get_imp_by_number(9999), MockStorageImp)

    def test_register_duplicate_number_conflict(self):
        """Test that duplicate imp numbers raise an error."""
        AddonRegistry.register("ADDON1", 1000, MockStorageImp)

        with self.assertRaises(ValueError) as context:
            AddonRegistry.register("ADDON2", 1000, MockCitationImp)
        self.assertIn("imp number conflict", str(context.exception))

    def test_register_same_addon_multiple_times(self):
        """Test that registering the same addon multiple times is allowed."""
        AddonRegistry.register("TEST_ADDON", 9999, MockStorageImp)
        # Should not raise an error
        AddonRegistry.register("TEST_ADDON", 9999, MockStorageImp)

        self.assertEqual(AddonRegistry.get_imp_by_name("TEST_ADDON"), MockStorageImp)

    def test_register_different_addon_same_number_error(self):
        """Test that different addons with same number raise error."""
        AddonRegistry.register("ADDON1", 1000, MockStorageImp)

        with self.assertRaises(ValueError):
            AddonRegistry.register("ADDON2", 1000, MockStorageImp)

    # Test 2: Retrieval Methods
    def test_get_imp_by_name_valid(self):
        """Test retrieving addon by valid name."""
        AddonRegistry.register("TEST_ADDON", 9999, MockStorageImp)
        result = AddonRegistry.get_imp_by_name("TEST_ADDON")
        self.assertEqual(result, MockStorageImp)

    def test_get_imp_by_name_invalid(self):
        """Test retrieving addon by invalid name raises KeyError."""
        with self.assertRaises(KeyError):
            AddonRegistry.get_imp_by_name("NONEXISTENT")

    def test_get_imp_by_number_valid(self):
        """Test retrieving addon by valid number."""
        AddonRegistry.register("TEST_ADDON", 9999, MockStorageImp)
        result = AddonRegistry.get_imp_by_number(9999)
        self.assertEqual(result, MockStorageImp)

    def test_get_imp_by_number_invalid(self):
        """Test retrieving addon by invalid number raises KeyError."""
        with self.assertRaises(KeyError):
            AddonRegistry.get_imp_by_number(99999)

    def test_get_imp_name(self):
        """Test getting name of registered imp."""
        AddonRegistry.register("TEST_ADDON", 9999, MockStorageImp)
        name = AddonRegistry.get_imp_name(MockStorageImp)
        self.assertEqual(name, "TEST_ADDON")

    def test_get_imp_name_unregistered(self):
        """Test getting name of unregistered imp raises ValueError."""
        with self.assertRaises(ValueError) as context:
            AddonRegistry.get_imp_name(MockCitationImp)
        self.assertIn("Unknown addon imp", str(context.exception))

    def test_get_imp_number(self):
        """Test getting number of registered imp."""
        AddonRegistry.register("TEST_ADDON", 9999, MockStorageImp)
        number = AddonRegistry.get_imp_number(MockStorageImp)
        self.assertEqual(number, 9999)

    def test_get_imp_number_unregistered(self):
        """Test getting number of unregistered imp raises ValueError."""
        with self.assertRaises(ValueError) as context:
            AddonRegistry.get_imp_number(MockCitationImp)
        self.assertIn("Unknown addon imp", str(context.exception))

    def test_get_all_addon_imps(self):
        """Test getting all registered addon imps."""
        AddonRegistry.register("ADDON1", 1001, MockStorageImp)
        AddonRegistry.register("ADDON2", 1002, MockCitationImp)

        all_imps = list(AddonRegistry.get_all_addon_imps())
        self.assertEqual(len(all_imps), 2)
        self.assertIn(MockStorageImp, all_imps)
        self.assertIn(MockCitationImp, all_imps)

    def test_iter_by_type_storage(self):
        """Test iterating addons by storage type."""
        AddonRegistry.register("STORAGE1", 1001, MockStorageImp)
        AddonRegistry.register("CITATION1", 1002, MockCitationImp)

        storage_addons = list(AddonRegistry.iter_by_type(StorageAddonImp))
        self.assertEqual(len(storage_addons), 1)
        self.assertEqual(storage_addons[0], (1001, "STORAGE1"))

    def test_iter_by_type_citation(self):
        """Test iterating addons by citation type."""
        AddonRegistry.register("STORAGE1", 1001, MockStorageImp)
        AddonRegistry.register("CITATION1", 1002, MockCitationImp)

        citation_addons = list(AddonRegistry.iter_by_type(CitationAddonImp))
        self.assertEqual(len(citation_addons), 1)
        self.assertEqual(citation_addons[0], (1002, "CITATION1"))

    def test_iter_by_type_no_filter(self):
        """Test iterating all addons."""
        AddonRegistry.register("STORAGE1", 1001, MockStorageImp)
        AddonRegistry.register("CITATION1", 1002, MockCitationImp)

        storage_addons = list(AddonRegistry.iter_by_type(AddonImp))
        self.assertEqual(len(storage_addons), 2)
        self.assertEqual(storage_addons[0], (1001, "STORAGE1"))
        self.assertEqual(storage_addons[1], (1002, "CITATION1"))

    # Test 3: Edge Cases & Error Handling
    def test_clear_registry(self):
        """Test clearing the registry."""
        AddonRegistry.register("TEST_ADDON", 9999, MockStorageImp)
        self.assertEqual(len(list(AddonRegistry.get_all_addon_imps())), 1)

        AddonRegistry.clear()
        self.assertEqual(len(list(AddonRegistry.get_all_addon_imps())), 0)

        with self.assertRaises(KeyError):
            AddonRegistry.get_imp_by_name("TEST_ADDON")

    def test_get_name_by_number_nonexistent(self):
        """Test getting name by nonexistent number raises KeyError."""
        with self.assertRaises(KeyError):
            AddonRegistry.get_name_by_number(99999)

    @patch("addon_service.common.known_imps.logger")
    def test_register_addon_apps_with_warning(self, mock_logger):
        """Test warning when addon in ADDON_APPS but not found."""
        addon_apps = {
            "NONEXISTENT_ADDON": 5000,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs", return_value=[]
        ):
            AddonRegistry.register_addon_apps(addon_apps)

        mock_logger.warning.assert_called_once()
        self.assertIn(
            "No addon app has name NONEXISTENT_ADDON",
            mock_logger.warning.call_args[0][0],
        )

    def test_register_addon_apps_with_known_addon(self):
        """Test registering known built-in addons through register_addon_apps."""
        addon_apps = {
            "BOX": 1001,
            "DROPBOX": 1006,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs", return_value=[]
        ):
            AddonRegistry.register_addon_apps(addon_apps)

        self.assertEqual(
            AddonRegistry.get_imp_by_number(1001), KnownAddonImps.BOX.value
        )
        self.assertEqual(
            AddonRegistry.get_imp_by_number(1006), KnownAddonImps.DROPBOX.value
        )
