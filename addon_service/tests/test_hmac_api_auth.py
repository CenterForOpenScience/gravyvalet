from datetime import (
    UTC,
    datetime,
    timedelta,
)
from http import HTTPStatus
from typing import Iterable
from unittest import mock

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.test import (
    RequestFactory,
    SimpleTestCase,
)
from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service.common import hmac as hmac_utils
from addon_service.common import osf
from addon_service.tests import _factories


class TestOsfUtilsHmac(SimpleTestCase):
    _fake_hmac_key = "so-secret-so-key"
    _fake_api_url = "https://fake.example/api"
    _fake_user_uri = "https://fake.example/user"
    _fake_resource_uri = "https://fake.example/resource"

    def setUp(self):
        super().setUp()
        self._mock_get_client = mock.AsyncMock()
        self.enterContext(
            mock.patch(
                "addon_service.common.osf.get_singleton_client_session",
                self._mock_get_client,
            )
        )
        self.enterContext(self.settings(OSF_HMAC_KEY=self._fake_hmac_key))

    def _fake_request(
        self,
        resource_permissions: Iterable[osf.OSFPermission] = (),
        resource_uri=None,
        user_uri=None,
    ):
        _additional_headers = {
            osf._OSF_HMAC_USER_HEADER: user_uri or self._fake_user_uri,
        }
        if resource_permissions:
            _additional_headers.update(
                {
                    osf._OSF_HMAC_RESOURCE_HEADER: resource_uri
                    or self._fake_resource_uri,
                    osf._OSF_HMAC_PERMISSIONS_HEADER: osf._OSF_HMAC_PERMISSIONS_DELIMITER.join(
                        resource_permissions
                    ),
                }
            )
        return RequestFactory().get(
            self._fake_api_url,
            headers=hmac_utils.make_signed_headers(
                request_url=self._fake_api_url,
                request_method="GET",
                hmac_key=self._fake_hmac_key,
                additional_headers=_additional_headers,
            ),
        )

    def test_get_osf_user_uri(self):
        _actual_user_uri = osf.get_osf_user_uri(self._fake_request())
        self.assertEqual(_actual_user_uri, self._fake_user_uri)
        self.assertFalse(self._mock_get_client.called)

    def test_get_osf_user_uri__wrong_key(self):
        with self.settings(OSF_HMAC_KEY="nope"):
            with self.assertRaises(PermissionDenied):
                osf.get_osf_user_uri(self._fake_request())

    def test_has_osf_permission_on_resource__read(self):
        _fake_request = self._fake_request([osf.OSFPermission.READ])
        self.assertTrue(
            osf.has_osf_permission_on_resource(
                _fake_request, self._fake_resource_uri, osf.OSFPermission.READ
            )
        )
        self.assertFalse(
            osf.has_osf_permission_on_resource(
                _fake_request, self._fake_resource_uri, osf.OSFPermission.WRITE
            )
        )
        self.assertFalse(
            osf.has_osf_permission_on_resource(
                _fake_request, self._fake_resource_uri, osf.OSFPermission.ADMIN
            )
        )
        self.assertFalse(
            osf.has_osf_permission_on_resource(
                _fake_request, "http://another.example/resource", osf.OSFPermission.READ
            )
        )
        self.assertFalse(
            self._mock_get_client.called,
            "should not try to send requests to osf when already hmac-verified",
        )

    def test_has_osf_permission_on_resource__admin(self):
        _fake_request = self._fake_request(osf.OSFPermission)
        self.assertTrue(
            osf.has_osf_permission_on_resource(
                _fake_request, self._fake_resource_uri, osf.OSFPermission.READ
            )
        )
        self.assertTrue(
            osf.has_osf_permission_on_resource(
                _fake_request, self._fake_resource_uri, osf.OSFPermission.WRITE
            )
        )
        self.assertTrue(
            osf.has_osf_permission_on_resource(
                _fake_request, self._fake_resource_uri, osf.OSFPermission.ADMIN
            )
        )
        self.assertFalse(
            osf.has_osf_permission_on_resource(
                _fake_request, "http://another.example/resource", osf.OSFPermission.READ
            )
        )
        self.assertFalse(self._mock_get_client.called)

    def test_has_osf_permission_on_resource__none(self):
        _fake_request = self._fake_request()
        self.assertFalse(
            osf.has_osf_permission_on_resource(
                _fake_request, self._fake_resource_uri, osf.OSFPermission.READ
            )
        )
        self.assertFalse(
            osf.has_osf_permission_on_resource(
                _fake_request, self._fake_resource_uri, osf.OSFPermission.WRITE
            )
        )
        self.assertFalse(
            osf.has_osf_permission_on_resource(
                _fake_request, self._fake_resource_uri, osf.OSFPermission.ADMIN
            )
        )
        self.assertFalse(
            osf.has_osf_permission_on_resource(
                _fake_request, "http://another.example/resource", osf.OSFPermission.READ
            )
        )
        self.assertFalse(
            self._mock_get_client.called,
            "should not try to send requests to osf when already hmac-verified",
        )

    def test_has_osf_permission_on_resource__wrong_key(self):
        with self.settings(OSF_HMAC_KEY="nope"):
            self.assertFalse(
                osf.has_osf_permission_on_resource(
                    self._fake_request([osf.OSFPermission.READ]),
                    self._fake_resource_uri,
                    osf.OSFPermission.READ,
                )
            )


class TestHmacApiAuth(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._resource = _factories.ResourceReferenceFactory()
        cls._service = _factories.ExternalStorageOAuth2ServiceFactory()
        cls._account = _factories.AuthorizedStorageAccountFactory(
            account_owner=cls._user,
            external_service=cls._service,
        )
        cls._addon = _factories.ConfiguredStorageAddonFactory(
            base_account=cls._account,
            authorized_resource=cls._resource,
        )

    def setUp(self):
        super().setUp()
        self._mock_get_client = mock.AsyncMock()
        self.enterContext(
            mock.patch(
                "addon_service.common.osf.get_singleton_client_session",
                self._mock_get_client,
            )
        )

    def test_valid_hmac_auth(self):
        _request_url = reverse(
            "configured-storage-addons-detail",
            kwargs={"pk": self._addon.pk},
        )
        _response = self.client.get(
            _request_url,
            headers=hmac_utils.make_signed_headers(
                request_url=_request_url,
                request_method="GET",
                hmac_key=settings.OSF_HMAC_KEY,
                additional_headers={
                    osf._OSF_HMAC_USER_HEADER: self._user.user_uri,
                    osf._OSF_HMAC_RESOURCE_HEADER: self._resource.resource_uri,
                    osf._OSF_HMAC_PERMISSIONS_HEADER: osf.OSFPermission.READ,
                },
            ),
        )
        self.assertTrue(HTTPStatus(_response.status_code).is_success)

    def test_hmac_error__invalid_signature(self):
        request_url = reverse(
            "configured-storage-addons-detail",
            kwargs={"pk": self._addon.pk},
        )
        response = self.client.get(
            request_url,
            headers=hmac_utils.make_signed_headers(
                request_url=request_url,
                request_method="GET",
                hmac_key="she'sabadbadkey",
                additional_headers={
                    osf._OSF_HMAC_USER_HEADER: self._user.user_uri,
                    osf._OSF_HMAC_RESOURCE_HEADER: self._resource.resource_uri,
                    osf._OSF_HMAC_PERMISSIONS_HEADER: osf.OSFPermission.READ,
                },
            ),
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_hmac_error__expired_header(self):
        request_url = reverse(
            "configured-storage-addons-detail",
            kwargs={"pk": self._addon.pk},
        )
        five_minutes_ago = datetime.now(UTC) - timedelta(minutes=5)
        with mock.patch("addon_service.common.hmac.datetime") as mock_datetime:
            mock_datetime.now.return_value = five_minutes_ago
            headers = hmac_utils.make_signed_headers(
                request_url=request_url,
                request_method="GET",
                hmac_key=settings.OSF_HMAC_KEY,
                additional_headers={
                    osf._OSF_HMAC_USER_HEADER: self._user.user_uri,
                    osf._OSF_HMAC_RESOURCE_HEADER: self._resource.resource_uri,
                    osf._OSF_HMAC_PERMISSIONS_HEADER: osf.OSFPermission.READ,
                },
            )
        response = self.client.get(request_url, headers=headers)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_hmac_error__future_header(self):
        request_url = reverse(
            "configured-storage-addons-detail",
            kwargs={"pk": self._addon.pk},
        )
        five_minutes_from_now = datetime.now(UTC) + timedelta(minutes=5)
        with mock.patch("addon_service.common.hmac.datetime") as mock_datetime:
            mock_datetime.now.return_value = five_minutes_from_now
            headers = hmac_utils.make_signed_headers(
                request_url=request_url,
                request_method="GET",
                hmac_key=settings.OSF_HMAC_KEY,
                additional_headers={
                    osf._OSF_HMAC_USER_HEADER: self._user.user_uri,
                    osf._OSF_HMAC_RESOURCE_HEADER: self._resource.resource_uri,
                    osf._OSF_HMAC_PERMISSIONS_HEADER: osf.OSFPermission.READ,
                },
            )
        response = self.client.get(request_url, headers=headers)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
