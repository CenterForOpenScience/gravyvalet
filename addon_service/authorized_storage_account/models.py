from django.contrib.postgres.fields import ArrayField
from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.int_capability import IntStorageCapability


class AuthorizedStorageAccount(AddonsServiceBaseModel):
    authorized_capabilities = ArrayField(
        models.IntegerField(choices=IntStorageCapability.as_django_choices()),
    )

    default_root_folder = models.CharField(blank=True)

    external_storage_service = models.ForeignKey(
        "addon_service.ExternalStorageService",
        on_delete=models.CASCADE,
        related_name="authorized_storage_accounts",
    )
    external_account = models.ForeignKey(
        "addon_service.ExternalAccount",
        on_delete=models.CASCADE,
        related_name="authorized_storage_accounts",
    )

    class Meta:
        verbose_name = "Authorized Storage Account"
        verbose_name_plural = "Authorized Storage Accounts"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "authorized-storage-accounts"

    @property
    def account_owner(self):
        return self.external_account.owner  # TODO: prefetch/select_related
