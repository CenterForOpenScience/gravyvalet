from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.known_imps import AddonImpNumbers
from addon_service.common.validators import validate_addon_capability
from addon_toolkit import (
    AddonCapabilities,
    AddonImp,
)
from app.celery import app


class ConnectedAddonManager(models.Manager):

    def active(self):
        """filter to addons owned by non-deactivated users"""
        return self.get_queryset().filter(
            base_account__account_owner__deactivated__isnull=True
        )


class ConfiguredAddon(AddonsServiceBaseModel):
    objects = ConnectedAddonManager()

    _display_name = models.CharField(null=False, blank=True, default="")
    int_connected_capabilities = models.IntegerField(
        validators=[validate_addon_capability]
    )
    base_account = models.ForeignKey(
        "addon_service.AuthorizedAccount",
        on_delete=models.CASCADE,
        related_name="configured_addons",
    )
    authorized_resource = models.ForeignKey(
        "addon_service.ResourceReference",
        on_delete=models.CASCADE,
        related_name="configured_addons",
    )

    @property
    def display_name(self):
        return self._display_name or self.base_account.display_name

    @display_name.setter
    def display_name(self, value: str):
        value = value if value is not None else ""
        self._display_name = value

    @property
    def connected_capabilities(self) -> AddonCapabilities:
        """get the enum representation of int_connected_capabilities"""
        return AddonCapabilities(self.int_connected_capabilities)

    @connected_capabilities.setter
    def connected_capabilities(self, new_capabilities: AddonCapabilities):
        """set int_connected_capabilities without caring it's int"""
        self.int_connected_capabilities = new_capabilities.value

    @property
    def account_owner(self):
        return self.base_account.account_owner

    @property
    def owner_uri(self) -> str:
        return self.base_account.owner_uri

    @property
    def resource_uri(self):
        return self.authorized_resource.resource_uri

    @resource_uri.setter
    def resource_uri(self, uri: str):
        from addon_service.resource_reference.models import ResourceReference

        _resource_ref, _ = ResourceReference.objects.get_or_create(resource_uri=uri)
        self.authorized_resource = _resource_ref

    @property
    def connected_operations(self) -> list[AddonOperationModel]:
        _imp_cls = self.imp_cls
        return [
            AddonOperationModel(_imp_cls, _operation)
            for _operation in _imp_cls.implemented_operations_for_capabilities(
                self.connected_capabilities
            )
        ]

    def save(self, *args, full_clean=True, **kwargs):
        id_ = self.pk
        super().save(*args, full_clean=full_clean, **kwargs)
        if not id_:  # If instance is created, not updated
            app.send_task(
                "osf.tasks.log_gv_addon",
                kwargs={
                    "node_url": self.resource_uri,
                    "user_url": self.owner_uri,
                    "addon": self.display_name,
                    "action": "addon_added",
                },
            )

    @property
    def connected_operation_names(self):
        return [
            _operation.name
            for _operation in self.imp_cls.implemented_operations_for_capabilities(
                self.connected_capabilities
            )
        ]

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        if result:
            app.send_task(
                "osf.tasks.log_gv_addon",
                kwargs={
                    "node_url": self.resource_uri,
                    "user_url": self.owner_uri,
                    "addon": self.display_name,
                    "action": "addon_removed",
                },
            )

    @property
    def credentials(self):
        return self.base_account.credentials

    @property
    def external_service(self):
        return self.base_account.external_service

    @property
    def imp_cls(self) -> type[AddonImp]:
        return self.base_account.imp_cls

    @property
    def external_service_name(self):
        number = self.base_account.external_service.int_addon_imp
        return AddonImpNumbers(number).name.lower()

    def clean_fields(self, *args, **kwargs):
        super().clean_fields(*args, **kwargs)
        _connected_caps = set(self.connected_capabilities)
        if not _connected_caps.issubset(self.base_account.authorized_capabilities):
            _unauthorized_caps = _connected_caps.difference(
                self.base_account.authorized_capabilities
            )
            raise ValidationError(
                {
                    "connected_capabilities": f"capabilities not authorized on account: {_unauthorized_caps}",
                }
            )
