import argparse
import pprint

from asgiref.sync import (
    async_to_sync,
    sync_to_async,
)
from django.conf import settings
from django.core.management.base import BaseCommand

from addon_service import models as db
from addon_service.common.aiohttp_session import (
    close_singleton_client_session__blocking,
)
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.invocation_status import InvocationStatus
from addon_service.common.known_imps import AddonRegistry
from addon_service.common.service_types import ServiceTypes
from addon_service.tasks.invocation import perform_invocation__blocking
from addon_toolkit import AddonCapabilities


class Command(BaseCommand):
    """list box root (temp command for local testing)

    to start, get an oauth2 `client_id` and `client_secret` on the external service.
    then, run `manage.py do_box_test authorize <client_id> <client_secret>`
    and follow instructions
    """

    def add_arguments(self, parser: argparse.ArgumentParser):
        _subparsers = parser.add_subparsers(required=True, title="test phase")
        _authorize = _subparsers.add_parser("authorize")
        _authorize.set_defaults(_test_phase="authorize")
        _authorize.add_argument("client_id")
        _authorize.add_argument("client_secret")
        _connect = _subparsers.add_parser("connect")
        _connect.set_defaults(_test_phase="connect")
        _connect.add_argument("account_id")
        _connect.add_argument("resource_uri")
        _invoke = _subparsers.add_parser("invoke")
        _invoke.set_defaults(_test_phase="invoke")
        _invoke.add_argument("addon_id")

    def handle(self, *args, **kwargs):
        if not settings.DEBUG:
            raise Exception(f"must have DEBUG set to use {self}")
        try:
            match kwargs["_test_phase"]:
                case "authorize":
                    self._setup_oauth(
                        "http://user.example/blarg",
                        client_id=kwargs["client_id"],
                        client_secret=kwargs["client_secret"],
                    )
                case "connect":
                    self._connect_addon(
                        account_id=kwargs["account_id"],
                        resource_uri=kwargs["resource_uri"],
                    )
                case "invoke":
                    self._do_invokes__blocking(kwargs)
                case _:
                    raise RuntimeError
        finally:
            close_singleton_client_session__blocking()

    def _setup_oauth(self, user_uri: str, client_id, client_secret):
        _user, _ = db.UserReference.objects.get_or_create(user_uri=user_uri)
        _oauth2_config = db.OAuth2ClientConfig.objects.create(
            auth_uri="https://www.box.com/api/oauth2/authorize",
            auth_callback_url="http://localhost:8004/v1/oauth/callback/",
            token_endpoint_url="https://www.box.com/api/oauth2/token",
            client_id=client_id,
            client_secret=client_secret,
        )
        _box_service, _ = db.ExternalStorageService.objects.update_or_create(
            int_addon_imp=AddonRegistry.get_imp_number(
                AddonRegistry.get_imp_by_name("BOX_DOT_COM")
            ),
            defaults=dict(
                name="my-box-dot-com",
                oauth2_client_config=_oauth2_config,
                api_base_url="https://api.box.com/2.0/",
                int_credentials_format=CredentialsFormats.OAUTH2.value,
                int_service_type=ServiceTypes.PUBLIC.value,
                supported_scopes=["root_readwrite"],
                max_concurrent_downloads=2,
                max_upload_mb=2,
            ),
        )
        _account = db.AuthorizedStorageAccount.objects.create(
            account_owner=_user,
            external_storage_service=_box_service,
            authorized_capabilities=AddonCapabilities.ACCESS | AddonCapabilities.UPDATE,
        )
        _account.initiate_oauth2_flow()
        self.stdout.write(
            self.style.SUCCESS("set up for oauth2! now do the flow in a browser:")
        )
        self.stdout.write(_account.auth_url)
        self.stdout.write(
            f"{self.style.SUCCESS('then run again with:')} do_box_test connect {_account.pk} <resource_uri>"
        )
        return _account

    def _connect_addon(self, account_id, resource_uri):
        _account = db.AuthorizedStorageAccount.objects.get(pk=account_id)
        _ir, _ = db.ResourceReference.objects.get_or_create(
            resource_uri="http://localhost:5000/haen7",
        )
        _configured_addon = db.ConfiguredStorageAddon.objects.create(
            base_account=_account,
            authorized_resource=_ir,
            connected_capabilities=AddonCapabilities.ACCESS,
        )
        self.stdout.write(
            f"{self.style.SUCCESS('connected! to invoke, run again with:')} do_box_test invoke {_configured_addon.pk}"
        )

    @async_to_sync
    async def _do_invokes__blocking(self, kwargs):
        await self._do_invoke(kwargs["addon_id"], "BOX_DOT_COM:list_root_items", {})
        await self._do_invoke(
            kwargs["addon_id"],
            "BOX_DOT_COM:list_child_items",
            {"item_id": "2:0"},
        )
        await self._do_invoke(
            kwargs["addon_id"],
            "BOX_DOT_COM:get_item_info",
            {"item_id": "1:1484968395678"},  # update with an actual item_id
        )

    @sync_to_async
    def _do_invoke(self, addon_id, op_id, op_kwargs):
        _configured_addon = db.ConfiguredStorageAddon.objects.get(pk=addon_id)
        _invocation = db.AddonOperationInvocation.objects.create(
            invocation_status=InvocationStatus.STARTING,
            operation_identifier=op_id,
            operation_kwargs=op_kwargs,
            thru_addon=_configured_addon,
            thru_account=_configured_addon.base_account,
            by_user=_configured_addon.account_owner,
        )
        perform_invocation__blocking(_invocation)
        for _attr_name in (
            "invocation_status",
            "operation_result",
            "exception_message",
            "exception_type",
            "exception_context",
        ):
            _attr_value = getattr(_invocation, _attr_name)
            if _attr_value not in (None, ""):
                self.stdout.write(
                    f"{self.style.SUCCESS(_attr_name)}: {pprint.pformat(_attr_value)}"
                )
