from urllib.parse import quote_plus

from django.core.management import BaseCommand
from django.db import transaction

from addon_service.authorized_account.citation.models import AuthorizedCitationAccount
from addon_service.authorized_account.computing.models import AuthorizedComputingAccount
from addon_service.authorized_account.storage.models import AuthorizedStorageAccount
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.configured_addon.citation.models import ConfiguredCitationAddon
from addon_service.configured_addon.computing.models import ConfiguredComputingAddon
from addon_service.configured_addon.storage.models import ConfiguredStorageAddon
from addon_service.external_service.models import ExternalService
from addon_service.oauth2 import OAuth2TokenMetadata
from addon_service.osf_models.models import (
    BitbucketNodeSettings,
    BitbucketUserSettings,
    BoaNodeSettings,
    BoaUserSettings,
    BoxNodeSettings,
    BoxUserSettings,
    DataverseNodeSettings,
    DataverseUserSettings,
    DropboxNodeSettings,
    DropboxUserSettings,
    ExternalAccount,
    FigshareNodeSettings,
    FigshareUserSettings,
    GithubNodeSettings,
    GithubUserSettings,
    GitlabNodeSettings,
    GitlabUserSettings,
    GoogleDriveNodeSettings,
    GoogleDriveUserSettings,
    Guid,
    MendeleyNodeSettings,
    MendeleyUserSettings,
    OneDriveNodeSettings,
    OneDriveUserSettings,
    OsfUser,
    OwnCloudNodeSettings,
    OwnCloudUserSettings,
    S3NodeSettings,
    S3UserSettings,
    UserToExternalAccount,
    ZoteroNodeSettings,
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


def fetch_external_accounts(user_id: int, provider: str):
    return [
        obj.externalaccount
        for obj in UserToExternalAccount.objects.select_related(
            "externalaccount"
        ).filter(osfuser_id=user_id)
        if obj.externalaccount.provider == provider
    ]


services = [
    ["storage", "dropbox", DropboxUserSettings, DropboxNodeSettings],
    ["storage", "bitbucket", BitbucketUserSettings, BitbucketNodeSettings],
    ["storage", "box", BoxUserSettings, BoxNodeSettings],
    ["storage", "github", GithubUserSettings, GithubNodeSettings],
    ["storage", "googledrive", GoogleDriveUserSettings, GoogleDriveNodeSettings],
    ["storage", "gitlab", GitlabUserSettings, GitlabNodeSettings],
    ["storage", "dataverse", DataverseUserSettings, DataverseNodeSettings],
    ["storage", "owncloud", OwnCloudUserSettings, OwnCloudNodeSettings],
    ["storage", "figshare", FigshareUserSettings, FigshareNodeSettings],
    ["storage", "onedrive", OneDriveUserSettings, OneDriveNodeSettings],
    ["storage", "s3", S3UserSettings, S3NodeSettings],
    ["citations", "mendeley", MendeleyUserSettings, MendeleyNodeSettings],
    ["citations", "zotero", ZoteroUserSettings, ZoteroNodeSettings],
    ["computing", "boa", BoaUserSettings, BoaNodeSettings],
]


def get_node_guid(id_):
    return Guid.objects.filter(content_type_id=7, object_id=id_).first()._id


OSF_BASE = settings.OSF_API_BASE_URL.replace("192.168.168.167", "localhost").replace(
    "8000", "5000"
)


def get_root_folder_for_provider(node_settings, service_name):
    match service_name:
        case "dropbox":
            return node_settings.folder
        case "box":
            return f"folder:{node_settings.folder_id}"
        case "github":
            return f"{node_settings.user}/{node_settings.repo}:"
        case "googledrive" | "onedrive" | "s3":
            return node_settings.folder_id
        case "owncloud":
            return f"folder:{node_settings.folder_id}"
        case "dataverse":
            return f"dataset/{node_settings._dataset_id}"
        case "gitlab":
            return quote_plus(f"{node_settings.user}/{node_settings.repo}") + ":"
        case "bitbucket":
            return f"repository:{node_settings.user}/{node_settings.repo}"
        case "zotero":
            return f"{node_settings.library_id}/{node_settings.list_id}"
        case "mendeley":
            return node_settings.list_id
        case "boa":
            return None


class Command(BaseCommand):
    @transaction.atomic
    def handle(self, *args, **options):
        for (
            integration_type,
            service_name,
            user_settings_class,
            node_settings_class,
        ) in services:
            for user_settings in user_settings_class.objects.all():
                try:
                    self.migrate_for_user(
                        integration_type,
                        service_name,
                        user_settings,
                        node_settings_class,
                    )
                except BaseException as e:
                    print(f"Failed to migrate {service_name} service with error {e}")
                    raise e

    def migrate_for_user(
        self, integration_type, service_name, user_settings, node_settings_class
    ):
        if integration_type == "storage":
            AuthorizedAccount = AuthorizedStorageAccount
            ConfiguredAddon = ConfiguredStorageAddon
        elif integration_type == "citations":
            AuthorizedAccount = AuthorizedCitationAccount
            ConfiguredAddon = ConfiguredCitationAddon
        elif integration_type == "computing":
            AuthorizedAccount = AuthorizedComputingAccount
            ConfiguredAddon = ConfiguredComputingAddon
        else:
            raise

        users_external_accounts = fetch_external_accounts(
            user_settings.owner_id, service_name
        )
        if not users_external_accounts:
            return
        osf_account: ExternalAccount = users_external_accounts[0]
        user = OsfUser.objects.get(pk=user_settings.owner_id)
        external_service = ExternalService.objects.filter(wb_key=service_name)[0]
        user_uri = f"{OSF_BASE}/{user.guid}"
        account_owner = UserReference.objects.get_or_create(user_uri=user_uri)
        credentials = self.get_credentials(external_service, osf_account)
        account = AuthorizedAccount(
            display_name=service_name.capitalize(),
            int_authorized_capabilities=(
                AddonCapabilities.UPDATE | AddonCapabilities.ACCESS
            ).value,
            account_owner=account_owner[0],
            external_service=external_service,
            credentials=credentials,
            external_account_id=osf_account.provider_id,
        )
        if external_service.credentials_format == CredentialsFormats.OAUTH2:
            token_metadata = OAuth2TokenMetadata(
                refresh_token=osf_account.refresh_token,
                access_token_expiration=osf_account.expires_at,
                authorized_scopes=external_service.supported_scopes,
            )
            token_metadata.save()
            account.oauth2_token_metadata = token_metadata

        if api_url := self.get_api_base_url(external_service, osf_account):
            account.api_base_url = api_url

        account.save()
        for node_settings in getattr(
            user_settings, f"{service_name}nodesettings_set"
        ).all():
            resource_reference = ResourceReference.objects.get_or_create(
                resource_uri=f"{OSF_BASE}/{get_node_guid(node_settings.owner_id)}"
            )[0]
            configured_addon = ConfiguredAddon(
                root_folder=get_root_folder_for_provider(node_settings, service_name),
                int_connected_capabilities=(
                    AddonCapabilities.UPDATE | AddonCapabilities.ACCESS
                ).value,
                base_account=account,
                authorized_resource=resource_reference,
            )
            configured_addon.save()

    def get_credentials(self, external_service, osf_account):
        if (
            external_service.credentials_format
            == CredentialsFormats.ACCESS_KEY_SECRET_KEY
        ):
            credentials = AccessKeySecretKeyCredentials(
                access_key=osf_account.oauth_key,
                secret_key=osf_account.oauth_secret,
            )
        elif (
            external_service.credentials_format == CredentialsFormats.USERNAME_PASSWORD
        ):
            credentials = UsernamePasswordCredentials(
                username=osf_account.display_name, password=osf_account.oauth_key
            )
        elif external_service.credentials_format == CredentialsFormats.OAUTH1A:
            credentials = OAuth1Credentials(
                oauth_token=osf_account.oauth_key,
                oauth_token_secret=osf_account.oauth_secret,
            )
        elif external_service.wb_key == "dataverse":
            credentials = AccessTokenCredentials(access_token=osf_account.oauth_secret)
        else:
            credentials = AccessTokenCredentials(access_token=osf_account.oauth_key)
        return credentials

    def get_api_base_url(self, external_service, osf_account):
        if external_service.wb_key == "owncloud":
            return f"{osf_account.profile_url.removesuffix('/')}/remote.php/dav/files/{osf_account.display_name}/"
        elif external_service.wb_key == "gitlab":
            return f"{osf_account.oauth_secret.removesuffix('/')}"
        elif external_service.wb_key == "dataverse":
            return f"https://{osf_account.oauth_key}"
