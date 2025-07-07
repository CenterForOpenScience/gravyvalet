import csv
import logging
from pathlib import Path
from typing import Any

from django.core.management import BaseCommand

from addon_service.external_service.citation.models import ExternalCitationService
from addon_service.external_service.computing.models import ExternalComputingService
from addon_service.external_service.link.models import ExternalLinkService
from addon_service.external_service.models import ExternalService
from addon_service.external_service.storage.models import ExternalStorageService
from addon_service.oauth1 import OAuth1ClientConfig
from addon_service.oauth2 import OAuth2ClientConfig


csv_base_path = Path(__file__).parent / "providers"
services_csv = csv_base_path / "providers.csv"
oauth2_csv = csv_base_path / "oauth2.csv"
oauth1_csv = csv_base_path / "oauth1.csv"

service_type_map = {
    "storage": ExternalStorageService,
    "citation": ExternalCitationService,
    "computing": ExternalComputingService,
    "link": ExternalLinkService,
}

icons_path = Path(__file__).parent.parent.parent / "static/provider_icons"
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        services = self.load_csv_data(services_csv)

        oauth2_configs = self.load_csv_data(oauth2_csv)
        oauth1_configs = self.load_csv_data(oauth1_csv)

        for service in services.values():
            model = service_type_map[service.pop("service_type")]
            service["icon_name"] = str(icons_path / service["icon_name"])
            if oauth2_id := service.pop("oauth2_client_config_id", None):
                oauth2_config = oauth2_configs[oauth2_id]
                oauth2_config = OAuth2ClientConfig.objects.create(**oauth2_config)
                service["oauth2_client_config"] = oauth2_config
            if oauth1_id := service.pop("oauth1_client_config_id", None):
                oauth1_config = oauth1_configs[oauth1_id]
                oauth1_config = OAuth1ClientConfig.objects.create(**oauth1_config)
                service["oauth1_client_config"] = oauth1_config
            logger.warning(f"Filled service {service['display_name']}")
            model.objects.create(**service)

    def load_csv_data(self, path: Path) -> dict[str, dict[str, Any]]:
        current_services_names = {
            service[0]
            for service in ExternalService.objects.values_list("display_name").all()
        }
        with path.open() as services_file:
            item = csv.reader(services_file)
            field_names = next(item)
            data_list = [dict(zip(field_names, service)) for service in item]
            return {
                item.pop("id"): self.fix_values(item)
                for item in data_list
                if item.get("display_name") not in current_services_names
            }

    def fix_values(self, item):
        raw_values = {key: self.fix_value(value) for key, value in item.items()}
        return {key: value for key, value in raw_values.items() if value is not None}

    def fix_value(self, data):
        if data == "":
            return None
        if data.startswith("{") and data.endswith("}"):
            values = data.removeprefix("{").removesuffix("}").split(",")
            if not values or not any(values):
                return None
            return values
        try:
            return int(data)
        except ValueError:
            pass
        return data
