from http import HTTPStatus

from django.test import SimpleTestCase
from django.urls import reverse


class TestOAuth2CallbackViewErrors(SimpleTestCase):
    def _get_error(self, **params):
        return self.client.get(reverse("oauth2-callback"), {"state": "1.n", **params})

    def test_known_error_code(self):
        _resp = self._get_error(error="access_denied", error_description="no thanks")
        self.assertEqual(_resp.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("access_denied", _resp.content.decode())
        self.assertNotIn("no thanks", _resp.content.decode())

    def test_error_params_are_not_reflected(self):
        with self.assertLogs("addon_service.oauth2.views", "WARNING"):
            _resp = self._get_error(
                error="<script>alert(1)</script>",
                error_description="<img src=x onerror=alert(2)>",
            )
        self.assertEqual(_resp.status_code, HTTPStatus.BAD_REQUEST)
        self.assertTrue(_resp["Content-Type"].startswith("text/plain"))
        self.assertNotIn("<script", _resp.content.decode())
        self.assertNotIn("<img", _resp.content.decode())
