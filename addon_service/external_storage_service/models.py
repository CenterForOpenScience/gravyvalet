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

    @staticmethod
    def get_ess_and_data_from_code(request):
        code = request.GET.get("code")
        state = request.GET.get("state")
        ess = ExternalStorageService.get(id=state['id'])
        credentials_issuer = ess.credentials_issuer

        query_params = {
            'redirect_uri': credentials_issuer.redirect_uri,
            'client_id': credentials_issuer.client_id,
            'client_secret': credentials_issuer.client_secret,
            'grant_type': 'authorization_code',
            'code': code
        }
        query_params = urllib.parse.urlencode(query_params)
        url = credentials_issuer.auth_url
        url += query_params
        resp = requests.post(url)
        data = resp.json()
        return ess, data