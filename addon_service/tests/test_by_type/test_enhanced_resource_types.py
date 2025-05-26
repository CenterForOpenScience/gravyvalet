from http import HTTPStatus

from django.test import (
    TestCase,
    override_settings,
)
from rest_framework.test import APITestCase

from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.enum_serializers import EnumNameMultipleChoiceField
from addon_service.tests import _factories
from addon_service.tests._helpers import MockOSF
from addon_toolkit.interfaces.link import SupportedResourceTypes


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TestResourceTypesSorting(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._external_service = _factories.ExternalLinkServiceFactory(
            supported_resource_types=SupportedResourceTypes.Dataset
            | SupportedResourceTypes.Book
            | SupportedResourceTypes.Software,
            credentials_format=CredentialsFormats.PERSONAL_ACCESS_TOKEN,
        )

    def setUp(self):
        super().setUp()
        self.client.cookies["osf"] = self._user.user_uri
        self._mock_osf = MockOSF()
        self._mock_osf.configure_assumed_caller(self._user.user_uri)
        self.enterContext(self._mock_osf.mocking())

    def test_external_service_resource_types_sorted_alphabetically(self):
        response = self.client.get(
            f"/v1/external-link-services/{self._external_service.id}/"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        resource_types = response.data.get("supported_resource_types", [])

        expected_order = ["Book", "Dataset", "Software"]
        self.assertEqual(resource_types, expected_order)

    def test_enum_field_returns_sorted_choices(self):
        expected_names = sorted([rt.name for rt in SupportedResourceTypes])

        actual_names = expected_names

        self.assertEqual(actual_names, expected_names)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TestResourceTypeValidation(TestCase):
    """Test validation of resource types"""

    def test_valid_resource_types(self):
        """Test that all supported resource types are valid"""
        valid_types = [
            SupportedResourceTypes.Book,
            SupportedResourceTypes.Dataset,
            SupportedResourceTypes.Software,
            SupportedResourceTypes.Journal,
            SupportedResourceTypes.OutputManagementPlan,
            SupportedResourceTypes.Other,
        ]

        for resource_type in valid_types:
            with self.subTest(resource_type=resource_type):
                addon = _factories.ConfiguredLinkAddonFactory()
                addon.resource_type = resource_type

                # Should not raise validation error
                addon.full_clean()
                self.assertEqual(addon.resource_type, resource_type)

    def test_resource_type_enum_values(self):
        self.assertEqual(SupportedResourceTypes.Dataset.name, "Dataset")
        self.assertEqual(SupportedResourceTypes.Book.name, "Book")
        self.assertEqual(SupportedResourceTypes.Software.name, "Software")
        self.assertEqual(SupportedResourceTypes.Journal.name, "Journal")
        self.assertEqual(
            SupportedResourceTypes.OutputManagementPlan.name, "OutputManagementPlan"
        )
        self.assertEqual(SupportedResourceTypes.Other.name, "Other")

    def test_resource_type_integer_conversion(self):
        addon = _factories.ConfiguredLinkAddonFactory()

        addon.resource_type = SupportedResourceTypes.Dataset
        addon.save()

        addon.refresh_from_db()
        self.assertEqual(addon.int_resource_type, SupportedResourceTypes.Dataset.value)
        self.assertEqual(addon.resource_type, SupportedResourceTypes.Dataset)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TestResourceTypeSerializerField(TestCase):

    def test_enum_field_serialization(self):
        field = EnumNameMultipleChoiceField(enum_cls=SupportedResourceTypes)

        result = field.to_representation(SupportedResourceTypes.Dataset)
        self.assertEqual(result, ["Dataset"])

        combined_value = SupportedResourceTypes.Dataset | SupportedResourceTypes.Book
        result = field.to_representation(combined_value)
        self.assertEqual(set(result), {"Dataset", "Book"})

    def test_enum_field_deserialization(self):
        field = EnumNameMultipleChoiceField(enum_cls=SupportedResourceTypes)

        result = field.to_internal_value(["Dataset"])
        self.assertEqual(result, SupportedResourceTypes.Dataset)

        result = field.to_internal_value(["Dataset", "Book"])
        expected = SupportedResourceTypes.Dataset | SupportedResourceTypes.Book
        self.assertEqual(result, expected)

    def test_enum_field_sorted_output(self):
        field = EnumNameMultipleChoiceField(enum_cls=SupportedResourceTypes)

        combined_value = (
            SupportedResourceTypes.Software
            | SupportedResourceTypes.Book
            | SupportedResourceTypes.Dataset
        )

        result = field.to_representation(combined_value)

        expected_order = ["Book", "Dataset", "Software"]
        self.assertEqual(result, expected_order)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TestResourceTypeNaming(TestCase):

    def test_output_management_plan_naming(self):
        resource_type = SupportedResourceTypes.OutputManagementPlan

        self.assertEqual(resource_type.name, "OutputManagementPlan")
        field = EnumNameMultipleChoiceField(enum_cls=SupportedResourceTypes)
        result = field.to_representation(resource_type)
        self.assertEqual(result, ["OutputManagementPlan"])

    def test_all_resource_type_names_valid(self):
        for resource_type in SupportedResourceTypes:
            with self.subTest(resource_type=resource_type):
                self.assertTrue(resource_type.name.isidentifier())

                self.assertNotIn(" ", resource_type.name)
                self.assertNotIn("-", resource_type.name)

    def test_resource_type_display_names(self):
        expected_names = {
            SupportedResourceTypes.Book: "Book",
            SupportedResourceTypes.Dataset: "Dataset",
            SupportedResourceTypes.Software: "Software",
            SupportedResourceTypes.Journal: "Journal",
            SupportedResourceTypes.OutputManagementPlan: "OutputManagementPlan",
            SupportedResourceTypes.Other: "Other",
        }

        for resource_type, expected_name in expected_names.items():
            with self.subTest(resource_type=resource_type):
                self.assertEqual(resource_type.name, expected_name)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TestResourceTypeAPIConsistency(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()

    def setUp(self):
        super().setUp()
        self.client.cookies["osf"] = self._user.user_uri
        self._mock_osf = MockOSF()
        self._mock_osf.configure_assumed_caller(self._user.user_uri)
        self.enterContext(self._mock_osf.mocking())


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TestResourceTypeCompatibility(TestCase):

    def test_resource_type_values_stable(self):
        known_values = {
            SupportedResourceTypes.Book: 4,
            SupportedResourceTypes.Dataset: 512,
            SupportedResourceTypes.Journal: 32768,
            SupportedResourceTypes.Other: 2147483648,
            SupportedResourceTypes.Software: 33554432,
            SupportedResourceTypes.OutputManagementPlan: 262144,
        }

        for resource_type, expected_value in known_values.items():
            with self.subTest(resource_type=resource_type):
                self.assertEqual(resource_type.value, expected_value)

    def test_resource_type_combinations(self):
        combined = SupportedResourceTypes.Dataset | SupportedResourceTypes.Book

        self.assertIn(SupportedResourceTypes.Dataset, combined)
        self.assertIn(SupportedResourceTypes.Book, combined)

        self.assertNotIn(SupportedResourceTypes.Software, combined)

        field = EnumNameMultipleChoiceField(enum_cls=SupportedResourceTypes)
        result = field.to_representation(combined)
        self.assertEqual(set(result), {"Dataset", "Book"})

    def test_legacy_resource_type_handling(self):
        addon = _factories.ConfiguredLinkAddonFactory(
            credentials_format=CredentialsFormats.PERSONAL_ACCESS_TOKEN,
        )

        addon.int_resource_type = None
        addon.save()

        addon.refresh_from_db()
        self.assertIsNone(addon.resource_type)

        addon.full_clean()
        addon.resource_type = SupportedResourceTypes.Other
        addon.save()
        addon.refresh_from_db()
        self.assertEqual(addon.resource_type, SupportedResourceTypes.Other)
