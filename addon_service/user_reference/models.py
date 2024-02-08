from django.db import models

from addon_service.authorized_storage_account.models import AuthorizedStorageAccount
from addon_service.common.base_model import AddonsServiceBaseModel


class InternalUser(AddonsServiceBaseModel):
    user_uri = models.URLField(unique=True, db_index=True, null=False)

    @property
    def authorized_storage_accounts(self):
        return AuthorizedStorageAccount.objects.filter(
            external_account__owner=self,
        )

    class Meta:
        verbose_name = "Internal User"
        verbose_name_plural = "Internal Users"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "internal-users"
