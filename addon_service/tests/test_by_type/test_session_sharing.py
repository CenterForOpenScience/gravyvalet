from http import HTTPStatus
from unittest.mock import (
    Mock,
    patch,
)

import itsdangerous
from django.conf import settings
from django.contrib.sessions.backends.cache import SessionStore
from django.test import (
    RequestFactory,
    TestCase,
)
from rest_framework.test import APITestCase

from addon_service.tests import _factories
from addon_service.tests._helpers import MockOSF
from app.middleware import UnsignCookieSessionMiddleware


class TestSessionSharingMiddleware(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = UnsignCookieSessionMiddleware(Mock())

    def test_process_request_with_valid_cookie(self):
        session_key = "test-session-key-123"
        signer = itsdangerous.Signer(settings.OSF_AUTH_COOKIE_SECRET)
        signed_cookie = signer.sign(session_key)

        request = self.factory.get("/")
        request.COOKIES = {settings.SESSION_COOKIE_NAME: signed_cookie}

        result = self.middleware.process_request(request)

        self.assertIsNone(result)
        self.assertIsInstance(request.session, SessionStore)
        self.assertEqual(request.session.session_key, session_key)

    def test_process_request_with_invalid_signature(self):
        invalid_cookie = "invalid.cookie.signature"

        request = self.factory.get("/")
        request.COOKIES = {settings.SESSION_COOKIE_NAME: invalid_cookie}

        result = self.middleware.process_request(request)

        self.assertIsNone(result)

    def test_process_request_without_cookie(self):
        request = self.factory.get("/")
        request.COOKIES = {}
        result = self.middleware.process_request(request)

        self.assertIsNone(result)
        self.assertIsInstance(request.session, SessionStore)
        self.assertIsNone(request.session.session_key)

    def test_process_request_with_empty_cookie(self):
        request = self.factory.get("/")
        request.COOKIES = {settings.SESSION_COOKIE_NAME: ""}

        result = self.middleware.process_request(request)

        self.assertIsNone(result)
        self.assertIsInstance(request.session, SessionStore)

    @patch("app.middleware.SessionStore")
    def test_session_store_instantiation(self, mock_session_store):
        session_key = "test-key-456"
        signer = itsdangerous.Signer(settings.OSF_AUTH_COOKIE_SECRET)
        signed_cookie = signer.sign(session_key)

        request = self.factory.get("/")
        request.COOKIES = {settings.SESSION_COOKIE_NAME: signed_cookie}

        self.middleware.process_request(request)

        mock_session_store.assert_called_with(session_key=session_key)


class TestRedisSessionBackend(TestCase):

    def test_session_engine_configuration(self):
        self.assertEqual(
            settings.SESSION_ENGINE, "django.contrib.sessions.backends.cache"
        )

    def test_redis_cache_configuration(self):
        cache_config = settings.CACHES["default"]
        self.assertEqual(
            cache_config["BACKEND"], "django.core.cache.backends.redis.RedisCache"
        )
        self.assertEqual(cache_config["LOCATION"], settings.REDIS_HOST)

    def test_session_cookie_name_matches_osf(self):
        self.assertEqual(settings.SESSION_COOKIE_NAME, settings.OSF_AUTH_COOKIE_NAME)


class TestSessionSharingIntegration(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls._user = _factories.UserReferenceFactory()
        cls._resource = _factories.ResourceReferenceFactory()

    def setUp(self):
        super().setUp()
        self._mock_osf = MockOSF()
        self._mock_osf.configure_assumed_caller(self._user.user_uri)
        self._mock_osf.configure_user_role(
            self._user.user_uri, self._resource.resource_uri, "admin"
        )
        self.enterContext(self._mock_osf.mocking())

    def test_api_access_with_shared_session(self):
        session_key = "shared-session-123"
        signer = itsdangerous.Signer(settings.OSF_AUTH_COOKIE_SECRET)
        signed_cookie = signer.sign(session_key)

        self.client.cookies[settings.OSF_AUTH_COOKIE_NAME] = signed_cookie

        session_store = SessionStore(session_key=session_key)
        session_store["user_reference_uri"] = self._user.user_uri
        session_store.save()

        url = f"/v1/resource-references/{self._resource.pk}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_session_persistence_across_requests(self):
        session_key = "persistent-session-456"
        signer = itsdangerous.Signer(settings.OSF_AUTH_COOKIE_SECRET)
        signed_cookie = signer.sign(session_key)

        self.client.cookies[settings.OSF_AUTH_COOKIE_NAME] = signed_cookie

        session_store = SessionStore(session_key=session_key)
        session_store["user_reference_uri"] = self._user.user_uri
        session_store["test_data"] = "persistent_value"
        session_store.save()

        url = f"/v1/resource-references/{self._resource.pk}/"
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, HTTPStatus.OK)

        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, HTTPStatus.OK)

        response3 = self.client.get(url)
        self.assertEqual(response3.status_code, HTTPStatus.OK)

        self.assertEqual(response1.data["id"], response2.data["id"])
        self.assertEqual(response2.data["id"], response3.data["id"])

    def test_invalid_session_handling(self):
        invalid_session_key = "invalid-session-789"
        signer = itsdangerous.Signer(settings.OSF_AUTH_COOKIE_SECRET)
        signed_cookie = signer.sign(invalid_session_key)

        self.client.cookies[settings.OSF_AUTH_COOKIE_NAME] = signed_cookie

        url = f"/v1/resource-references/{self._resource.pk}/"
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            [
                HTTPStatus.OK,  # MockOSF allows access
                HTTPStatus.UNAUTHORIZED,
                HTTPStatus.FORBIDDEN,
            ],
        )


class TestCookieSigningCompatibility(TestCase):

    def test_cookie_signing_with_osf_secret(self):
        test_value = "test-session-value"
        signer = itsdangerous.Signer(settings.OSF_AUTH_COOKIE_SECRET)
        signed_value = signer.sign(test_value)
        self.assertIsInstance(signed_value, (str, bytes))

        unsigned_value = signer.unsign(signed_value)
        self.assertEqual(
            (
                unsigned_value.decode()
                if isinstance(unsigned_value, bytes)
                else unsigned_value
            ),
            test_value,
        )

    def test_bad_signature_handling(self):
        signer = itsdangerous.Signer(settings.OSF_AUTH_COOKIE_SECRET)

        with self.assertRaises(itsdangerous.BadSignature):
            signer.unsign("tampered.signature.value")

    def test_cookie_secret_configuration(self):
        self.assertIsNotNone(settings.OSF_AUTH_COOKIE_SECRET)
        self.assertNotEqual(settings.OSF_AUTH_COOKIE_SECRET, "CHANGEME")
        self.assertTrue(len(settings.OSF_AUTH_COOKIE_SECRET) > 10)


class TestSessionSecurityFeatures(TestCase):

    def test_cors_credentials_enabled(self):
        self.assertTrue(settings.CORS_ALLOW_CREDENTIALS)

    @patch("app.middleware.ensure_str")
    def test_session_key_encoding(self, mock_ensure_str):
        mock_ensure_str.return_value = "encoded-session-key"

        session_key = b"binary-session-key"
        signer = itsdangerous.Signer(settings.OSF_AUTH_COOKIE_SECRET)
        signed_cookie = signer.sign(session_key)

        request = RequestFactory().get("/")
        request.COOKIES = {settings.SESSION_COOKIE_NAME: signed_cookie}

        middleware = UnsignCookieSessionMiddleware(Mock())
        middleware.process_request(request)

        mock_ensure_str.assert_called_once()
