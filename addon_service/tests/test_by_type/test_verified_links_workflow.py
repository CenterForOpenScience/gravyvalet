from unittest.mock import (
    MagicMock,
    patch,
)

from django.test import TestCase
from rest_framework.test import APITestCase

from addon_service.external_service.link.models import LinkSupportedFeatures
from addon_service.tests import _factories
from addon_toolkit.interfaces.link import SupportedResourceTypes


class TestVerifiedLinksWorkflow(APITestCase):

    def setUp(self):
        self._service = _factories.ExternalLinkOAuth2ServiceFactory(
            display_name="Dataverse Link Service",
            supported_features=LinkSupportedFeatures.ADD_UPDATE_FILES,
        )
        self._account = _factories.AuthorizedLinkAccountFactory(
            external_service=self._service
        )

    @patch("app.celery.app.send_task")
    def test_create_link_addon_workflow(self, mock_send_task):
        addon = _factories.ConfiguredLinkAddonFactory(
            external_link_service=self._service,
            base_account=self._account,
            target_id="dataset_123",
            resource_type=SupportedResourceTypes.Dataset,
        )

        addon.resource_uri = "https://osf.io/abc123/"
        addon.save()

        self.assertIsNotNone(addon.pk)
        self.assertEqual(addon.target_id, "dataset_123")
        self.assertEqual(addon.resource_uri, "https://osf.io/abc123/")

        mock_send_task.assert_called()


class TestCeleryIntegration(TestCase):

    def setUp(self):
        self._service = _factories.ExternalLinkOAuth2ServiceFactory(
            display_name="Test Service",
            supported_features=LinkSupportedFeatures.ADD_UPDATE_FILES,
        )
        self._account = _factories.AuthorizedLinkAccountFactory(
            external_service=self._service
        )

    @patch("app.celery.app.send_task")
    def test_celery_task_on_complete_addon(self, mock_send_task):
        addon = _factories.ConfiguredLinkAddonFactory(
            external_link_service=self._service,
            base_account=self._account,
            target_id="dataset_123",
            resource_type=SupportedResourceTypes.Dataset,
        )

        addon.resource_uri = "https://osf.io/abc123/"
        addon.save()

        self.assertTrue(mock_send_task.called)
        call_args_list = mock_send_task.call_args_list

        log_calls = [
            call for call in call_args_list if "osf.tasks.log_gv_addon" in call[0]
        ]
        self.assertTrue(len(log_calls) > 0)

    @patch("app.celery.app.send_task")
    def test_celery_task_not_triggered_incomplete(self, mock_send_task):
        addon = _factories.ConfiguredLinkAddonFactory(
            external_link_service=self._service,
            base_account=self._account,
            target_id="",
            resource_type=SupportedResourceTypes.Dataset,
        )

        addon.resource_uri = "https://osf.io/abc123/"
        addon.save()

        self.assertTrue(mock_send_task.called)
        call_args_list = mock_send_task.call_args_list

        log_calls = [
            call for call in call_args_list if "osf.tasks.log_gv_addon" in call[0]
        ]
        verification_calls = [
            call
            for call in call_args_list
            if "website.identifiers.tasks.task__update_verified_links" in call[0]
        ]

        self.assertTrue(len(log_calls) > 0)
        self.assertEqual(len(verification_calls), 0)


class TestMultipleAddonsPerResource(TestCase):

    def setUp(self):
        self._service1 = _factories.ExternalLinkOAuth2ServiceFactory(
            display_name="Dataverse",
            supported_features=LinkSupportedFeatures.ADD_UPDATE_FILES,
        )
        self._service2 = _factories.ExternalLinkOAuth2ServiceFactory(
            display_name="Zenodo",
            supported_features=LinkSupportedFeatures.ADD_UPDATE_FILES,
        )

        self._account1 = _factories.AuthorizedLinkAccountFactory(
            external_service=self._service1
        )
        self._account2 = _factories.AuthorizedLinkAccountFactory(
            external_service=self._service2
        )

    @patch("app.celery.app.send_task")
    def test_multiple_addons_same_resource(self, mock_send_task):
        resource_uri = "https://osf.io/abc123/"

        addon1 = _factories.ConfiguredLinkAddonFactory(
            external_link_service=self._service1,
            base_account=self._account1,
            target_id="dataverse_dataset_123",
            resource_type=SupportedResourceTypes.Dataset,
        )
        addon1.resource_uri = resource_uri
        addon1.save()

        addon2 = _factories.ConfiguredLinkAddonFactory(
            external_link_service=self._service2,
            base_account=self._account2,
            target_id="zenodo_record_456",
            resource_type=SupportedResourceTypes.Dataset,
        )
        addon2.resource_uri = resource_uri
        addon2.save()

        self.assertIsNotNone(addon1.pk)
        self.assertIsNotNone(addon2.pk)
        self.assertEqual(addon1.resource_uri, addon2.resource_uri)
        self.assertNotEqual(addon1.target_id, addon2.target_id)


class TestDataverseLinkIntegration(TestCase):
    """Test Dataverse-specific link functionality."""

    def setUp(self):
        self._service = _factories.ExternalLinkOAuth2ServiceFactory(
            display_name="Harvard Dataverse",
            browser_base_url="https://dataverse.harvard.edu/",
            supported_features=LinkSupportedFeatures.ADD_UPDATE_FILES,
        )
        self._account = _factories.AuthorizedLinkAccountFactory(
            external_service=self._service
        )

    @patch("addon_service.addon_imp.instantiation.get_link_addon_instance__blocking")
    @patch("app.celery.app.send_task")
    def test_dataverse_url_generation(self, mock_send_task, mock_get_instance):
        async def mock_build_url(target_id):
            return "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/12345"

        mock_addon = MagicMock()
        mock_addon.build_url_for_id = mock_build_url
        mock_get_instance.return_value = mock_addon

        addon = _factories.ConfiguredLinkAddonFactory(
            external_link_service=self._service,
            base_account=self._account,
            target_id="dataset/doi:10.7910/DVN/12345",
            resource_type=SupportedResourceTypes.Dataset,
        )
        addon.resource_uri = "https://osf.io/abc123/"
        addon.save()

        target_url = addon.target_url()
        self.assertIsNotNone(target_url)
        self.assertIn("dataverse.harvard.edu", target_url)

    @patch("app.celery.app.send_task")
    def test_different_resource_types(self, mock_send_task):
        """Test creating addons with different resource types."""
        addon1 = _factories.ConfiguredLinkAddonFactory(
            external_link_service=self._service,
            base_account=self._account,
            target_id="dataset_123",
            resource_type=SupportedResourceTypes.Dataset,
        )
        addon1.resource_uri = "https://osf.io/abc123/"
        addon1.save()

        addon2 = _factories.ConfiguredLinkAddonFactory(
            external_link_service=self._service,
            base_account=self._account,
            target_id="article_456",
            resource_type=SupportedResourceTypes.JournalArticle,
        )
        addon2.resource_uri = "https://osf.io/def456/"
        addon2.save()

        self.assertEqual(addon1.resource_type, SupportedResourceTypes.Dataset)
        self.assertEqual(addon2.resource_type, SupportedResourceTypes.JournalArticle)

    @patch("app.celery.app.send_task")
    def test_target_url_with_empty_target_id(self, mock_send_task):
        """Test that target_url returns None when target_id is empty."""
        addon = _factories.ConfiguredLinkAddonFactory(
            external_link_service=self._service,
            base_account=self._account,
            target_id="",
            resource_type=SupportedResourceTypes.Dataset,
        )
        addon.resource_uri = "https://osf.io/abc123/"
        addon.save()

        self.assertIsNone(addon.target_url())


class TestResourceValidation(TestCase):

    def setUp(self):
        self._service = _factories.ExternalLinkOAuth2ServiceFactory(
            display_name="Test Service",
            supported_features=LinkSupportedFeatures.ADD_UPDATE_FILES,
        )
        self._account = _factories.AuthorizedLinkAccountFactory(
            external_service=self._service
        )

    @patch("app.celery.app.send_task")
    def test_addon_creation_with_valid_resource_uri(self, mock_send_task):
        valid_uris = [
            "https://osf.io/abc123/",
            "https://staging.osf.io/def456/",
            "http://localhost:5000/xyz789/",
        ]

        for uri in valid_uris:
            with self.subTest(uri=uri):
                addon = _factories.ConfiguredLinkAddonFactory(
                    external_link_service=self._service,
                    base_account=self._account,
                    target_id="test_123",
                    resource_type=SupportedResourceTypes.Dataset,
                )
                addon.resource_uri = uri
                addon.save()
                self.assertEqual(addon.resource_uri, uri)

    @patch("app.celery.app.send_task")
    def test_addon_creation_different_resource_uris(self, mock_send_task):
        uris = [
            "https://osf.io/project1/",
            "https://osf.io/project2/",
            "https://staging.osf.io/project3/",
        ]

        addons = []
        for i, uri in enumerate(uris):
            addon = _factories.ConfiguredLinkAddonFactory(
                external_link_service=self._service,
                base_account=self._account,
                target_id=f"target_{i}",
                resource_type=SupportedResourceTypes.Dataset,
            )
            addon.resource_uri = uri
            addon.save()
            addons.append(addon)

        for addon in addons:
            self.assertIsNotNone(addon.pk)

        uri_set = {addon.resource_uri for addon in addons}
        self.assertEqual(len(uri_set), len(addons))
