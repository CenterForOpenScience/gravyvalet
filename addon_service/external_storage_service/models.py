import urllib
import requests
from django.contrib.postgres.fields import ArrayField
from django.db import models

from addon_service.addon_imp.known import get_imp_by_number
from addon_service.addon_imp.models import AddonImpModel
from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.enums.validators import validate_storage_imp_number


class ExternalStorageService(AddonsServiceBaseModel):
    int_addon_imp = models.IntegerField(
        null=False,
        validators=[validate_storage_imp_number],
    )
    default_scopes = ArrayField(models.CharField(), null=True, blank=True)
    max_concurrent_downloads = models.IntegerField(null=False)
    max_upload_mb = models.IntegerField(null=False)
    auth_uri = models.URLField(null=False)
    callback_url = models.URLField(null=False, default="")

    credentials_issuer = models.ForeignKey(
        "addon_service.CredentialsIssuer",
        on_delete=models.CASCADE,
        related_name="external_storage_services",
    )

    class Meta:
        verbose_name = "External Storage Service"
        verbose_name_plural = "External Storage Services"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "external-storage-services"

    def get_oauth_data_from_request(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state")

        query_params = {
            'redirect_uri': state.redirect_uri,
            'client_id': state.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code
        }
        query_params = urllib.parse.urlencode(query_params)
        url = self.callback_url
        url += query_params
        resp = requests.post(url)
        data = resp.json()
        return data

    @property
    def addon_imp(self) -> AddonImpModel:
        return AddonImpModel(get_imp_by_number(self.int_addon_imp))
