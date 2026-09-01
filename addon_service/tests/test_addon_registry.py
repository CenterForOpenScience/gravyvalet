"""Tests for the AddonImpRegistry class."""

from unittest.mock import patch

from django.test import TestCase

from addon_service.common.known_imps import (
    AddonImpRegistry,
    KnownAddonImps,
)
from addon_toolkit import AddonImp
from addon_toolkit.interfaces.citation import CitationAddonImp
from addon_toolkit.interfaces.storage import StorageAddonImp


class MockStorageImp(StorageAddonImp):
    """Mock storage addon imp for testing."""


class MockCitationImp(CitationAddonImp):
    """Mock citation addon imp for testing."""


class TestAddonImpRegistry(TestCase):
    """Test cases for AddonImpRegistry class."""

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

    # Test 1: Registration Mechanics
    def test_register_addon_imp_success(self):
        """Test successful registration of an addon imp."""
        AddonImpRegistry.register("TEST_ADDON_IMP", 9999, MockStorageImp)

        self.assertEqual(
            AddonImpRegistry.get_imp_by_name("TEST_ADDON_IMP"), MockStorageImp
        )
        self.assertEqual(AddonImpRegistry.get_name_by_number(9999), "TEST_ADDON_IMP")
        self.assertEqual(AddonImpRegistry.get_imp_by_number(9999), MockStorageImp)

    def test_register_duplicate_number_conflict(self):
        """Test that duplicate imp numbers raise an error."""
        AddonImpRegistry.register("ADDON_IMP1", 1000, MockStorageImp)

        with self.assertRaises(ValueError) as context:
            AddonImpRegistry.register("ADDON_IMP2", 1000, MockCitationImp)
        self.assertIn("imp number conflict", str(context.exception))

    def test_register_same_addon_imp_multiple_times(self):
        """Test that registering the same addon imp multiple times is allowed."""
        AddonImpRegistry.register("TEST_ADDON_IMP", 9999, MockStorageImp)
        # Should not raise an error
        AddonImpRegistry.register("TEST_ADDON_IMP", 9999, MockStorageImp)

        self.assertEqual(
            AddonImpRegistry.get_imp_by_name("TEST_ADDON_IMP"), MockStorageImp
        )

    def test_register_different_addon_imp_same_number_error(self):
        """Test that different addon imps with the same number raise error."""
        AddonImpRegistry.register("ADDON_IMP1", 1000, MockStorageImp)

        with self.assertRaises(ValueError):
            AddonImpRegistry.register("ADDON_IMP2", 1000, MockStorageImp)

    # Test 2: Retrieval Methods
    def test_get_imp_by_name_valid(self):
        """Test retrieving addon imp by a valid name."""
        AddonImpRegistry.register("TEST_ADDON_IMP", 9999, MockStorageImp)
        result = AddonImpRegistry.get_imp_by_name("TEST_ADDON_IMP")
        self.assertEqual(result, MockStorageImp)

    def test_get_imp_by_name_invalid(self):
        """Test retrieving addon imp by an invalid name raises KeyError."""
        with self.assertRaises(KeyError):
            AddonImpRegistry.get_imp_by_name("NONEXISTENT")

    def test_get_imp_by_number_valid(self):
        """Test retrieving addon imp by a valid number."""
        AddonImpRegistry.register("TEST_ADDON_IMP", 9999, MockStorageImp)
        result = AddonImpRegistry.get_imp_by_number(9999)
        self.assertEqual(result, MockStorageImp)

    def test_get_imp_by_number_invalid(self):
        """Test retrieving addon imp by an invalid number raises KeyError."""
        with self.assertRaises(KeyError):
            AddonImpRegistry.get_imp_by_number(99999)

    def test_get_imp_name(self):
        """Test getting name of registered imp."""
        AddonImpRegistry.register("TEST_ADDON_IMP", 9999, MockStorageImp)
        name = AddonImpRegistry.get_imp_name(MockStorageImp)
        self.assertEqual(name, "TEST_ADDON_IMP")

    def test_get_imp_name_unregistered(self):
        """Test getting the name of an unregistered imp raises ValueError."""
        with self.assertRaises(ValueError) as context:
            AddonImpRegistry.get_imp_name(MockCitationImp)
        self.assertIn("Unknown addon imp", str(context.exception))

    def test_get_imp_number(self):
        """Test getting the number of a registered imp."""
        AddonImpRegistry.register("TEST_ADDON_IMP", 9999, MockStorageImp)
        number = AddonImpRegistry.get_imp_number(MockStorageImp)
        self.assertEqual(number, 9999)

    def test_get_imp_number_unregistered(self):
        """Test getting the number of an unregistered imp raises ValueError."""
        with self.assertRaises(ValueError) as context:
            AddonImpRegistry.get_imp_number(MockCitationImp)
        self.assertIn("Unknown addon imp", str(context.exception))

    def test_get_all_addon_imps(self):
        """Test getting all registered addon imps."""
        AddonImpRegistry.register("ADDON_IMP1", 1001, MockStorageImp)
        AddonImpRegistry.register("ADDON_IMP2", 1002, MockCitationImp)

        all_imps = list(AddonImpRegistry.get_all_addon_imps())
        self.assertEqual(len(all_imps), 2)
        self.assertIn(MockStorageImp, all_imps)
        self.assertIn(MockCitationImp, all_imps)

    def test_iter_by_type_storage(self):
        """Test iterating addon imps by storage type."""
        AddonImpRegistry.register("STORAGE1", 1001, MockStorageImp)
        AddonImpRegistry.register("CITATION1", 1002, MockCitationImp)

        storage_addon_imps = list(AddonImpRegistry.iter_by_type(StorageAddonImp))
        self.assertEqual(len(storage_addon_imps), 1)
        self.assertEqual(storage_addon_imps[0], (1001, "STORAGE1"))

    def test_iter_by_type_citation(self):
        """Test iterating addon imps by citation type."""
        AddonImpRegistry.register("STORAGE1", 1001, MockStorageImp)
        AddonImpRegistry.register("CITATION1", 1002, MockCitationImp)

        citation_addon_imps = list(AddonImpRegistry.iter_by_type(CitationAddonImp))
        self.assertEqual(len(citation_addon_imps), 1)
        self.assertEqual(citation_addon_imps[0], (1002, "CITATION1"))

    def test_iter_by_type_no_filter(self):
        """Test iterating all addon imps."""
        AddonImpRegistry.register("STORAGE1", 1001, MockStorageImp)
        AddonImpRegistry.register("CITATION1", 1002, MockCitationImp)

        addon_imps = list(AddonImpRegistry.iter_by_type(AddonImp))
        self.assertEqual(len(addon_imps), 2)
        self.assertEqual(addon_imps[0], (1001, "STORAGE1"))
        self.assertEqual(addon_imps[1], (1002, "CITATION1"))

    # Test 3: Edge Cases & Error Handling
    def test_clear_registry(self):
        """Test clearing the registry."""
        AddonImpRegistry.register("TEST_ADDON_IMP", 9999, MockStorageImp)
        self.assertEqual(len(list(AddonImpRegistry.get_all_addon_imps())), 1)

        AddonImpRegistry.clear()
        self.assertEqual(len(list(AddonImpRegistry.get_all_addon_imps())), 0)

        with self.assertRaises(KeyError):
            AddonImpRegistry.get_imp_by_name("TEST_ADDON_IMP")

    def test_get_name_by_number_nonexistent(self):
        """Test getting names by a nonexistent number raises KeyError."""
        with self.assertRaises(KeyError):
            AddonImpRegistry.get_name_by_number(99999)

    @patch("addon_service.common.known_imps.logger")
    def test_register_addon_imps_with_warning(self, mock_logger):
        """Test warning when an addon imp is in ADDON_IMPS but not found."""
        ADDON_IMPS = {
            "NONEXISTENT_ADDON_IMP": 5000,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs", return_value=[]
        ):
            AddonImpRegistry.register_addon_imps(ADDON_IMPS)

        mock_logger.warning.assert_called_once()
        self.assertIn(
            "No addon imp has name NONEXISTENT_ADDON_IMP",
            mock_logger.warning.call_args[0][0],
        )

    def test_register_addon_imps_with_known_addon_imps(self):
        """Test registering known built-in addon imps through register_addon_imps."""
        addon_imps = {
            "BOX": 1001,
            "DROPBOX": 1006,
        }

        with patch(
            "addon_service.common.known_imps.apps.get_app_configs", return_value=[]
        ):
            AddonImpRegistry.register_addon_imps(addon_imps)

        self.assertEqual(
            AddonImpRegistry.get_imp_by_number(1001), KnownAddonImps.BOX.value
        )
        self.assertEqual(
            AddonImpRegistry.get_imp_by_number(1006), KnownAddonImps.DROPBOX.value
        )
