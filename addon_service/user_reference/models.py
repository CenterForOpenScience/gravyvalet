from django.db import models
from django.utils import timezone

from addon_service.authorized_storage_account.models import AuthorizedStorageAccount
from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.configured_storage_addon.models import ConfiguredStorageAddon
from addon_service.external_account.models import ExternalAccount


class UserReference(AddonsServiceBaseModel):
    user_uri = models.URLField(unique=True, db_index=True, null=False)
    deactivated = models.DateTimeField(null=True, blank=True)

    @property
    def authorized_storage_accounts(self):
        return AuthorizedStorageAccount.objects.filter(
            external_account__owner=self,
        )

    @property
    def configured_storage_addons(self):
        return ConfiguredStorageAddon.objects.filter(
            base_account__external_account__owner=self,
        )

    class Meta:
        verbose_name = "User Reference"
        verbose_name_plural = "User References"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "user-references"

    @property
    def owner_uri(self) -> str:
        return self.user_uri

    def deactivate(self):
        self.deactivated = timezone.now()
        self.save()

    def delete(self, force=False):
        """
        For preventing hard deletes use deactivate instead.
        """
        if force:
            return super().delete()
        raise NotImplementedError(
            "This is to prevent hard deletes, use deactivate or force=True."
        )

    def reactivate(self):
        # TODO: Logging?
        self.deactivated = None
        self.save()

    def merge(self, merge_with):
        """
        This represents the user "being merged into", the "merge_with" is the old account that is deactivated.
        """
        ExternalAccount.objects.filter(owner=merge_with).update(owner=self)
        merge_with.deactivate()
