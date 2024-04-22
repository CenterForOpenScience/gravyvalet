from django.conf import settings
from django.core.management.base import BaseCommand

from addon_service import models as db
from addon_service.addon_imp.known import get_imp_by_name

# from addon_service.addon_operation_invocation.perform import perform_invocation__async
# from addon_service.common.invocation import InvocationStatus
from addon_service.credentials import CredentialsFormats
from addon_service.external_storage_service import ServiceTypes
from addon_toolkit import AddonCapabilities


class Command(BaseCommand):
    """list box root (temp command for local testing)"""

    def handle(self, **options):
        if not settings.DEBUG:
            raise Exception(f"must have DEBUG set to use {self}")
        _user, _ = db.UserReference.objects.get_or_create(
            user_uri="http://user.example/blarg",
        )
        self._setup_addon(_user)
        # _invocation = db.AddonOperationInvocation.objects.create(
        #     invocation_status=InvocationStatus.STARTING,
        #     operation_identifier="BOX_DOT_COM:get_root_items",
        #     operation_kwargs={},
        #     thru_addon=_addon,
        #     by_user=_user,
        # )
        # asyncio.run(perform_invocation__async(_invocation))
        # for _attr in (
        #     "invocation_status",
        #     "operation_result",
        #     "exception_message",
        #     "exception_type",
        #     "exception_context",
        # ):
        #     print(f"{_attr}: {pprint.pformat(getattr(_invocation, _attr))}")

    def _setup_addon(self, user: db.UserReference):
        _oauth2_config = db.OAuth2ClientConfig.objects.create(
            auth_uri="https://www.box.com/api/oauth2/authorize",
            auth_callback_url="http://localhost:8004/v1/oauth/callback/",
            # auth_callback_url="http://localhost:5000/oauth/callback/box/",
            token_endpoint_url="https://www.box.com/api/oauth2/token",
            client_id="xfsuitb3abwqbk2gaxbx29cqwlpdedrx",
            client_secret="...",
        )
        _box_service, _ = db.ExternalStorageService.objects.update_or_create(
            int_addon_imp=get_imp_by_name("BOX_DOT_COM").imp_number,
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
            account_owner=user,
            external_storage_service=_box_service,
            authorized_capabilities=AddonCapabilities.ACCESS | AddonCapabilities.UPDATE,
        )
        _account.initiate_oauth2_flow()
        print(_account.auth_url)
        # _ir, _ = db.ResourceReference.objects.get_or_create(
        #     resource_uri="http://osf.example/blarg",
        # )
        # return db.ConfiguredStorageAddon.objects.create(
        #     base_account=_account,
        #     authorized_resource=_ir,
        #     connected_capabilities=AddonCapabilities.ACCESS,
        # )
