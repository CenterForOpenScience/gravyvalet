import logging

from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import (
    Count,
    F,
)

from addon_service.authorized_account.citation.models import AuthorizedCitationAccount
from addon_service.authorized_account.computing.models import AuthorizedComputingAccount
from addon_service.authorized_account.storage.models import AuthorizedStorageAccount
from addon_service.osf_models.models import (
    ExternalAccount,
    UserToExternalAccount,
)


logger = logging.getLogger(__name__)

services = {
    "dropbox": "storage",
    "bitbucket": "storage",
    "box": "storage",
    "github": "storage",
    "googledrive": "storage",
    "figshare": "storage",
    "onedrive": "storage",
    "mendeley": "citations",
}


def get_class(integration_type):
    if integration_type == "storage":
        return AuthorizedStorageAccount
    elif integration_type == "citations":
        return AuthorizedCitationAccount
    elif integration_type == "computing":
        return AuthorizedComputingAccount
    else:
        raise


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--fake", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        shared_ids = (
            UserToExternalAccount.objects.values("externalaccount")
            .annotate(count=Count("osfuser"))
            .filter(count__gte=2)
        )
        shared_accounts = ExternalAccount.objects.filter(
            id__in=[item.get("externalaccount") for item in shared_ids],
            provider__in=services.keys(),
        )
        for account in shared_accounts:
            integration_type = services[account.provider]
            AuthorizedAccount = get_class(integration_type)
            accounts = (
                AuthorizedAccount.objects.filter(
                    external_account_id=account.provider_id,
                )
                .select_related("oauth2_token_metadata", "_credentials")
                .order_by(
                    F("oauth2_token_metadata__date_last_refreshed").desc(
                        nulls_last=True
                    )
                )
            )
            # take the first account here because it has the most recently refreshed credentials,
            # and update all credentials/token metadata with first_account's ones
            token_metadata = accounts[0].oauth2_token_metadata
            credentials = accounts[0]._credentials
            accounts.update(
                oauth2_token_metadata=token_metadata, _credentials=credentials
            )
        if options.get("fake"):
            transaction.set_rollback(True)
