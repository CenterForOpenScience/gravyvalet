from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel


class ServiceCredential(AddonsServiceBaseModel):
    """
    Represents the credentials for an external service in the Addons Service.
    """
    name = models.CharField(max_length=255, blank=False, null=False)

    def retrieve_credentials(self, validated_data):
        """
        Retrieves credentials from validated data.
        """
        return [validated_data.get('username'), validated_data.get('password')]

    def check_credentials(self, credentials):
        """
        Method for checking the validity credentials.
        """
        return credentials

    def coerce_credentials_into_db_terms(self, credentials):
        """
        Coerces user credentials into database-compatible terms.
        """
        return {
            'oauth_key': credentials[0],
            'oauth_secret': credentials[1]
        }

    class Meta:
        verbose_name = "External Service"
        verbose_name_plural = "External Services"
        app_label = "addon_service"
