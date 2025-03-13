import logging

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Count

from addon_service.authorized_account.citation.models import AuthorizedCitationAccount
from addon_service.authorized_account.storage.models import AuthorizedStorageAccount
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.configured_addon.citation.models import ConfiguredCitationAddon
from addon_service.configured_addon.storage.models import ConfiguredStorageAddon
from addon_service.external_service.models import ExternalService
from addon_service.osf_models.models import (
    BitbucketUserSettings,
    BoxUserSettings,
    DataverseUserSettings,
    DropboxUserSettings,
    ExternalAccount,
    FigshareUserSettings,
    GithubUserSettings,
    GitlabUserSettings,
    GoogleDriveUserSettings,
    Guid,
    MendeleyUserSettings,
    OneDriveUserSettings,
    OsfUser,
    OwnCloudUserSettings,
    S3UserSettings,
    ZoteroUserSettings,
)
from addon_service.resource_reference.models import ResourceReference
from addon_service.user_reference.models import UserReference
from addon_toolkit import AddonCapabilities
from addon_toolkit.credentials import (
    AccessKeySecretKeyCredentials,
    AccessTokenCredentials,
    OAuth1Credentials,
    UsernamePasswordCredentials,
)
from app import settings


logger = logging.getLogger(__name__)

provider_to_user_settings = {
    "dropbox": DropboxUserSettings,
    "bitbucket": BitbucketUserSettings,
    "box": BoxUserSettings,
    "github": GithubUserSettings,
    "googledrive": GoogleDriveUserSettings,
    "gitlab": GitlabUserSettings,
    "dataverse": DataverseUserSettings,
    "owncloud": OwnCloudUserSettings,
    "figshare": FigshareUserSettings,
    "onedrive": OneDriveUserSettings,
    "s3": S3UserSettings,
    "mendeley": MendeleyUserSettings,
    "zotero": ZoteroUserSettings,
}
storage_provider = [
    "dropbox",
    "bitbucket",
    "box",
    "github",
    "googledrive",
    "gitlab",
    "dataverse",
    "owncloud",
    "figshare",
    "onedrive",
    "s3",
]
citation_provider = ["mendeley", "zotero"]

OSF_BASE = settings.OSF_BASE_URL.replace("192.168.168.167", "localhost").replace(
    "8000", "5000"
)


class CredentialException(Exception):
    pass


# Ported over from migrate_authorized_account.py
def get_credentials(
    external_service: ExternalService, external_account: ExternalAccount
):
    if external_service.credentials_format == CredentialsFormats.ACCESS_KEY_SECRET_KEY:
        check_fields(external_account, ["oauth_key", "oauth_secret"])
        credentials = AccessKeySecretKeyCredentials(
            access_key=external_account.oauth_key,
            secret_key=external_account.oauth_secret,
        )
    elif external_service.credentials_format == CredentialsFormats.USERNAME_PASSWORD:
        check_fields(external_account, ["display_name", "oauth_key"])
        credentials = UsernamePasswordCredentials(
            username=external_account.display_name, password=external_account.oauth_key
        )
    elif external_service.credentials_format == CredentialsFormats.OAUTH1A:
        check_fields(external_account, ["oauth_key", "oauth_secret"])
        credentials = OAuth1Credentials(
            oauth_token=external_account.oauth_key,
            oauth_token_secret=external_account.oauth_secret,
        )
    elif external_service.wb_key == "dataverse":
        check_fields(external_account, ["oauth_secret"])
        credentials = AccessTokenCredentials(access_token=external_account.oauth_secret)
    elif external_service.wb_key == "dropbox" and not external_account.refresh_token:
        check_fields(external_account, ["oauth_key"])
        credentials = AccessTokenCredentials(access_token=external_account.oauth_key)
    else:
        check_fields(external_account, ["oauth_key"])
        credentials = AccessTokenCredentials(access_token=external_account.oauth_key)
    return credentials


# Ported over from migrate_authorized_account.py
def check_fields(external_account: ExternalAccount, fields: list[str]):
    errors = []
    for field in fields:
        if getattr(external_account, field, None) is None:
            error_string = f"Required field <<{field}>> is None"
            errors.append(error_string)
    if errors:
        raise CredentialException(errors)


# Ported over from migrate_authorized_account.py
def get_node_guid(id_):
    content_type_id = cache.get_or_set(
        "node_contenttype_id",
        lambda: ContentType.objects.using("osf")
        .get(app_label="osf", model="abstractnode")
        .id,
        timeout=None,
    )
    return (
        Guid.objects.filter(content_type_id=content_type_id, object_id=id_).first()._id
    )


# return a list of tuples of (user_guid, provider_name_with_duplicate_accounts)
def get_target_user_guids_and_provider():
    return (
        ExternalAccount.objects.values("osfuser__guids___id", "provider")
        .annotate(account_per_provider=Count("id"))
        .filter(account_per_provider__gt=1)
        .values_list("osfuser__guids___id", "provider")
    )


def get_node_settings_for_user_and_provider(user_guid, provider):
    UserSettings = provider_to_user_settings[provider]
    user_setting = UserSettings.objects.get(
        owner=OsfUser.objects.get(guids___id=user_guid)
    )
    return getattr(user_setting, f"{provider}nodesettings_set").all()


def get_configured_addon(node_guid, provider):
    resource_reference = ResourceReference.objects.get_or_create(
        resource_uri=f"{OSF_BASE}/{node_guid}"
    )[0]
    if provider in storage_provider:
        ConfiguredAddon = ConfiguredStorageAddon
    elif provider in citation_provider:
        ConfiguredAddon = ConfiguredCitationAddon

    try:
        configured_addon = ConfiguredAddon.objects.get(
            authorized_resource=resource_reference
        )
    except ConfiguredAddon.DoesNotExist:
        print("ConfiguredAddon not found")

    return configured_addon


def get_external_service(provider):
    return ExternalService.objects.get(wb_key=provider)


def get_user_reference(user_guid):
    return UserReference.objects.get_or_create(user_uri=f"{OSF_BASE}/{user_guid}")


def get_or_create_authorized_account(external_account, provider, user_guid):
    if provider in storage_provider:
        AuthorizedAccount = AuthorizedStorageAccount
    elif provider in citation_provider:
        AuthorizedAccount = AuthorizedCitationAccount

    external_service = get_external_service(provider)
    account_owner = get_user_reference(user_guid)

    authorized_account = None
    if not AuthorizedAccount.objects.filter(
        external_account_id=external_account.id,
        external_service=external_service,
        account_owner=account_owner,
    ).exists():
        credentials = get_credentials(external_service, external_account)
        authorized_account = AuthorizedAccount(
            display_name=external_service.display_name.capitalize(),
            int_authorized_capabilities=(
                AddonCapabilities.UPDATE | AddonCapabilities.ACCESS
            ).value,
            account_owner=account_owner,
            external_service=external_service,
            credentials=credentials,
            external_account_id=external_account.provider_id,
        )
    else:
        authorized_account = AuthorizedAccount.objects.get(
            external_account_id=external_account.id,
            external_service=external_service,
            account_owner=account_owner,
        )

    return authorized_account


# check to see if the ConfiguredAddon's base account has the same
# external_account_id as the ExternalAccount's provider_id
def configured_addon_has_correct_base_account(external_account, node_guid, provider):
    configured_addon = get_configured_addon(node_guid, provider)
    if (
        configured_addon.base_account.external_account_id
        == external_account.provider_id
    ):
        return True
    return False


def fix_migration_for_user_and_provider(user_guid, provider):
    if not user_guid:
        return

    for node_settings in get_node_settings_for_user_and_provider(user_guid, provider):
        external_account = node_settings.external_account
        node_guid = get_node_guid(node_settings.owner_id)

        # check to see if the migrated configured_addon instance have the authorized account with the same external_account_id
        if not configured_addon_has_correct_base_account(
            external_account, node_guid, provider
        ):
            # if not, then we fix it
            configured_addon = get_configured_addon(node_guid, provider)
            authorized_account = get_or_create_authorized_account(
                external_account, provider, user_guid
            )
            configured_addon.base_account = authorized_account
            configured_addon.save()


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--fake", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        fake = options["fake"]

        for user_guid, provider in get_target_user_guids_and_provider():
            fix_migration_for_user_and_provider(user_guid, provider)
        if fake:
            print("Rolling back the transactions because this is a fake run")
            transaction.set_rollback(True)
