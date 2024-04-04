from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel


class ExternalAccount(AddonsServiceBaseModel):
    credentials_issuer = models.ForeignKey(
        "addon_service.CredentialsIssuer",
        on_delete=models.CASCADE,
        related_name="external_accounts",
    )
    owner = models.ForeignKey(
        "addon_service.UserReference",
        on_delete=models.CASCADE,
        related_name="external_accounts",
    )
    credentials = models.ForeignKey(
        "addon_service.ExternalCredentials",
        on_delete=models.CASCADE,
        related_name="external_accounts",
    )

    class Meta:
        verbose_name = "External Account"
        verbose_name_plural = "External Accounts"
        app_label = "addon_service"
