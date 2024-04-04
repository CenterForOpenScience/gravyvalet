from django.conf import settings
from django.core.management.base import LabelCommand

from addon_service import models as db
from addon_service.addon_imp.known import get_imp_by_name
from addon_service.common.invocation import InvocationStatus
from addon_toolkit import AddonCapabilities


class Command(LabelCommand):
    """add garbage to the database for local/manual testing

    provide one or more labels; will create one set of connected objects for each label
    """

    def handle_label(self, label, **options):
        if not settings.DEBUG:
            raise Exception("must have DEBUG set to eat garbage")
        _ci = db.CredentialsIssuer.objects.create(name=f"entity-{label}")
        _ess = db.ExternalStorageService.objects.create(
            int_addon_imp=get_imp_by_name("BLARG").imp_number,
            max_concurrent_downloads=2,
            max_upload_mb=2,
            auth_uri=f"http://foo.example/{label}",
            credentials_issuer=_ci,
        )
        for _i in range(3):
            _iu, _ = db.UserReference.objects.get_or_create(
                user_uri=f"http://osf.example/u{label}{_i}",
            )
            _ec = db.ExternalCredentials.objects.create()
            _ea = db.ExternalAccount.objects.create(
                credentials_issuer=_ci,
                owner=_iu,
                credentials=_ec,
            )
            _asa = db.AuthorizedStorageAccount.objects.create(
                external_storage_service=_ess,
                external_account=_ea,
                authorized_capabilities=[
                    AddonCapabilities.ACCESS,
                    AddonCapabilities.UPDATE,
                ],
            )
            for _op in _asa.authorized_operations:
                _ir, _ = db.ResourceReference.objects.get_or_create(
                    resource_uri=f"http://osf.example/r{label}{_op.name}",
                )
                _csa = db.ConfiguredStorageAddon.objects.create(
                    base_account=_asa,
                    authorized_resource=_ir,
                    connected_capabilities=[AddonCapabilities.ACCESS],
                )
                _soi = db.AddonOperationInvocation.objects.create(
                    invocation_status=InvocationStatus.STARTING,
                    operation_identifier=_op.natural_key_str,
                    operation_kwargs={"item": {"item_id": "foo"}, "page": {}},
                    thru_addon=_csa,
                    by_user=_iu,
                )
        return str(_soi)
