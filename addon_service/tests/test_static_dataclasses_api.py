from django.urls import reverse
from rest_framework.test import APITestCase

from addon_service.common import known_imps


class TestAddonImpsView(APITestCase):
    def test_get(self):
        _resp = self.client.get(reverse("addon-imps-list"))
        _data = _resp.json()["data"]
        _expected_names = {_imp.name for _imp in known_imps.KnownAddonImps}
        _actual_names = {_datum["attributes"]["name"] for _datum in _data}
        self.assertEqual(_expected_names, _actual_names)

    def test_unallowed_methods(self): ...


class TestAddonOperationsView(APITestCase):
    def test_get(self):
        _resp = self.client.get(reverse("addon-operations-list"))
        _data = _resp.json()["data"]
        _expected_names = {
            _op.name
            for _imp in known_imps.KnownAddonImps
            for _op in _imp.value.all_implemented_operations()
        }
        _actual_names = {_datum["attributes"]["name"] for _datum in _data}
        self.assertEqual(_expected_names, _actual_names)
