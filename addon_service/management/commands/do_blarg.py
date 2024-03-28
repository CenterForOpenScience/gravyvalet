from django.conf import settings
from django.core.management.base import BaseCommand

from addon_service import models as db
from addon_service.addon_imp.known import get_imp_by_name
from addon_service.addon_operation_invocation.perform import (
    perform_invocation__blocking,
)
from addon_service.common.invocation import InvocationStatus
from addon_toolkit import AddonCapabilities


class Command(BaseCommand):
    """list box root (temp command for local testing)"""

    def handle(self, **options):
        if not settings.DEBUG:
            raise Exception(f"must have DEBUG set to use {self}")
        _user, _ = db.UserReference.objects.get_or_create(
            user_uri="http://user.example/blarg",
        )
        _addon = self._setup_addon(_user)
        _invocation = db.AddonOperationInvocation.objects.create(
            invocation_status=InvocationStatus.STARTING,
            operation_identifier="BOX_DOT_COM:get_root_items",
            operation_kwargs={"item": {"item_id": "foo"}, "page": {}},
            thru_addon=_addon,
            by_user=_user,
        )
        perform_invocation__blocking(_invocation)
        print(f"{_invocation.invocation_status=}, {_invocation.operation_result=}")

    def _setup_addon(self, user: db.UserReference) -> db.ConfiguredStorageAddon:
        _box_ci, _ = db.CredentialsIssuer.objects.get_or_create(name="box.com")
        _box_service, _ = db.ExternalStorageService.objects.get_or_create(
            int_addon_imp=get_imp_by_name("BOX_DOT_COM").imp_number,
            defaults=dict(
                max_concurrent_downloads=2,
                max_upload_mb=2,
                api_base_url="http://box.example/foo/",  # TODO
                auth_uri="http://box.example/fakeauth/",
                credentials_issuer=_box_ci,
            ),
        )
        _ec = db.ExternalCredentials.objects.create()
        _ea = db.ExternalAccount.objects.create(
            credentials_issuer=_box_ci,
            owner=user,
            credentials=_ec,
        )
        _account = db.AuthorizedStorageAccount.objects.create(
            external_storage_service=_box_service,
            external_account=_ea,
            authorized_capabilities=[
                AddonCapabilities.ACCESS,
                AddonCapabilities.UPDATE,
            ],
        )
        _ir, _ = db.ResourceReference.objects.get_or_create(
            resource_uri="http://osf.example/blarg",
        )
        return db.ConfiguredStorageAddon.objects.create(
            base_account=_account,
            authorized_resource=_ir,
            connected_capabilities=[AddonCapabilities.ACCESS],
        )
