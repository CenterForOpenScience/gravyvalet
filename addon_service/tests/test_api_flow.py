from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service import models as db
from addon_service.tests import _factories


class TestCrudFlow(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # assumed to be set up thru admin interface, read-only in the api
        cls._external_service = _factories.ExternalStorageServiceFactory()
        # (TODO: user/resource created implicitly)
        cls._internal_user = _factories.InternalUserFactory()
        cls._internal_resource = _factories.InternalResourceFactory()

    def test_create_read_update_delete(self):
        _account = self._create_authorized_account()
        self.assertNotNone(_account)
        # _addon = self._create_configured_addon()

    def _create_authorized_account(self):
        _default_root_folder = "/hello/hello/"
        _account_post_body = {
            "data": {
                "type": _resource_type(db.AuthorizedStorageAccount),
                "attributes": {
                    "default_root_folder": _default_root_folder,
                },
                # TODO: attributes
                "relationships": {
                    "account_owner": {
                        "data": _resource_ref(self._internal_user),
                    },
                    "external_storage_service": {
                        "data": _resource_ref(self._external_service),
                    },
                },
            },
        }
        _create_account_resp = self.client.post(
            _path__create(db.AuthorizedStorageAccount),
            _account_post_body,
        )
        _create_resp_json = _create_account_resp.json()
        _account_pk = _create_resp_json["data"]["id"]
        _db_account = db.AuthorizedStorageAccount.objects.get(pk=_account_pk)
        self.assertEqual(_default_root_folder, _db_account.default_root_folder)
        self.assertEqual(
            _default_root_folder,
            _create_resp_json["data"]["attributes"]["default_root_folder"],
        )
        return _db_account


##
# helpers for the tests above


def _resource_type(something):
    try:
        return something.JSONAPIMeta.resource_name
    except AttributeError:
        raise ValueError(f"unsure how to type {something}")


def _path__create(model_cls):
    return reverse(f"{_resource_type(model_cls)}-list")


def _path__by_pk(model_cls, pk):
    return reverse(
        f"{_resource_type(model_cls)}-detail",
        kwargs={"pk": pk},
    )


def _resource_ref(model_instance):
    # jsonapi resource reference
    return {
        "type": model_instance.JSONAPIMeta.resource_name,
        "id": model_instance.pk,
    }
