import urllib
import requests
from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel


class ExternalStorageService(AddonsServiceBaseModel):
    max_concurrent_downloads = models.IntegerField(null=False)
    max_upload_mb = models.IntegerField(null=False)

    auth_uri = models.URLField(null=False)

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