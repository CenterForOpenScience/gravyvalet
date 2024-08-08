from django.conf import settings
from django.core.management.base import LabelCommand

from addon_service import models as db
from addon_service.common import known_imps
from addon_service.credentials.enums import CredentialsFormats
from addon_toolkit import AddonCapabilities


class Command(LabelCommand):
    """add garbage to the database for local/manual testing

    provide one or more labels; will create one set of connected objects for each label
    """

    def handle_label(self, label, **options):
        if not settings.DEBUG:
            raise Exception("must have DEBUG set to eat garbage")
        _blarg_imp = known_imps.get_imp_by_name("BLARG")
        _ess = db.ExternalStorageService.objects.create(
            service_name=label,
            addon_imp=db.AddonImpModel(_blarg_imp),
            int_credentials_format=CredentialsFormats.PERSONAL_ACCESS_TOKEN.value,
            max_concurrent_downloads=2,
            max_upload_mb=2,
            api_base_url=f"http://foo.example/{label}/",
        )
        _userref, _ = db.UserReference.objects.get_or_create(
            user_uri=f"http://osf.example/u{label}",
        )
        _asa = db.AuthorizedStorageAccount.objects.create(
            external_storage_service=_ess,
            account_owner=_userref,
            authorized_capabilities=[
                AddonCapabilities.ACCESS,
                AddonCapabilities.UPDATE,
            ],
        )
        _resourceref, _ = db.ResourceReference.objects.get_or_create(
            resource_uri=f"http://osf.example/r{label}",
        )
        _addon = db.ConfiguredStorageAddon.objects.create(
            base_account=_asa,
            authorized_resource=_resourceref,
            connected_capabilities=[AddonCapabilities.ACCESS],
        )
        _invocation = db.AddonOperationInvocation.objects.create(
            operation_identifier="STORAGE:list_root_items",
            operation_kwargs={"item": {"item_id": "foo"}, "page": {}},
            thru_addon=_addon,
            by_user=_userref,
        )
        return str(_invocation)
