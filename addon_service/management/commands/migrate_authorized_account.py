import logging
from urllib.parse import quote_plus

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import (
    BaseCommand,
    CommandError,
)
from django.db import transaction
from tqdm import tqdm

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


logger = logging.getLogger(__name__)


def fetch_external_accounts(user_id: int, provider: str):
    return [
        obj.externalaccount
        for obj in UserToExternalAccount.objects.select_related(
            "externalaccount"
        ).filter(osfuser_id=user_id)
        if obj.externalaccount.provider == provider
    ]


class CredentialException(Exception):
    pass


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

SERVICE_CHOICES = [service[1] for service in services]


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


OSF_BASE = settings.OSF_BASE_URL.replace("192.168.168.167", "localhost").replace(
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
            return f"collection:{node_settings.library_id}:{node_settings.list_id}"
        case "mendeley":
            return f"collection:{node_settings.list_id}"
        case "boa":
            return None
        case "figshare":
            folder_type = (
                node_settings.folder_path
                if node_settings.folder_path == "project"
                else "article"
            )
            return f"{folder_type}/{node_settings.folder_id}".replace(
                "dataset", "article"
            )


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "--only", nargs="*", type=str, default=None, choices=SERVICE_CHOICES
        )
        parser.add_argument(
            "--without", nargs="*", type=str, default=None, choices=SERVICE_CHOICES
        )
        parser.add_argument("--fake", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        fake = options["fake"]
        services_to_migrate = self._get_services_to_migrate(options)
        for (
            integration_type,
            service_name,
            user_settings_class,
            node_settings_class,
        ) in services_to_migrate:
            external_service = ExternalService.objects.filter(wb_key=service_name)[0]
            for user_settings in tqdm(
                user_settings_class.objects.all(), f"Migrating users for {service_name}"
            ):
                try:
                    self.migrate_for_user(
                        integration_type, service_name, user_settings, external_service
                    )
                except BaseException as e:
                    print(
                        f"Failed to migrate {service_name} for user with pk={user_settings.owner_id}service with error {e}"
                    )
                    raise e
        if fake:
            print("Rolling back the transactions because this is a fake run")
            transaction.set_rollback(True)

    def _get_services_to_migrate(self, options) -> list:
        only = options["only"]
        without = options["without"]
        if only and without:
            raise CommandError(
                "Cannot provide both --only and --without at the same time"
            )
        if only:
            return [service for service in services if service[1] in only]
        elif without:
            return [service for service in services if service[1] not in without]
        return services

    def migrate_for_user(
        self, integration_type, service_name, user_settings, external_service
    ):
        node_settings_set = getattr(
            user_settings, f"{service_name}nodesettings_set"
        ).all()
        if not node_settings_set:
            return

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
        user = OsfUser.objects.get(pk=user_settings.owner_id)
        account_map = {}
        for osf_account in users_external_accounts:
            try:
                credentials = self.get_credentials(external_service, osf_account)
            except CredentialException as e:
                logger.error(
                    f"Skipping account migration with {osf_account.pk=} for service {external_service.display_name} "
                    f"due to credentials parse error {e=}"
                )
                return
            user_uri = f"{OSF_BASE}/{user.guid}"
            account_owner = UserReference.objects.get_or_create(user_uri=user_uri)
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
                token_metadata.save(full_clean=False)
                account.oauth2_token_metadata = token_metadata

            if api_url := self.get_api_base_url(external_service, osf_account):
                try:
                    account.api_base_url = api_url
                except ValidationError:
                    print(api_url)

            account.save(full_clean=False)
            account_map[osf_account.id] = account

        for node_settings in node_settings_set:
            node_guid = get_node_guid(node_settings.owner_id)
            resource_reference = ResourceReference.objects.get_or_create(
                resource_uri=f"{OSF_BASE}/{node_guid}"
            )[0]
            base_account = account_map.get(node_settings.external_account.id)
            configured_addon = ConfiguredAddon(
                int_connected_capabilities=(
                    AddonCapabilities.UPDATE | AddonCapabilities.ACCESS
                ).value,
                base_account=base_account,
                authorized_resource=resource_reference,
            )
            root_folder = get_root_folder_for_provider(node_settings, service_name)
            if root_folder is not None:
                configured_addon.root_folder = root_folder
            configured_addon.save()

    def get_credentials(
        self, external_service: ExternalService, osf_account: ExternalAccount
    ):
        if (
            external_service.credentials_format
            == CredentialsFormats.ACCESS_KEY_SECRET_KEY
        ):
            self.check_fields(osf_account, ["oauth_key", "oauth_secret"])
            credentials = AccessKeySecretKeyCredentials(
                access_key=osf_account.oauth_key,
                secret_key=osf_account.oauth_secret,
            )
        elif (
            external_service.credentials_format == CredentialsFormats.USERNAME_PASSWORD
        ):
            self.check_fields(osf_account, ["display_name", "oauth_key"])
            credentials = UsernamePasswordCredentials(
                username=osf_account.display_name, password=osf_account.oauth_key
            )
        elif external_service.credentials_format == CredentialsFormats.OAUTH1A:
            self.check_fields(osf_account, ["oauth_key", "oauth_secret"])
            credentials = OAuth1Credentials(
                oauth_token=osf_account.oauth_key,
                oauth_token_secret=osf_account.oauth_secret,
            )
        elif external_service.wb_key == "dataverse":
            self.check_fields(osf_account, ["oauth_secret"])
            credentials = AccessTokenCredentials(access_token=osf_account.oauth_secret)
        elif external_service.wb_key == "dropbox" and not osf_account.refresh_token:
            # Dropbox updated their Oauth2 access token policy to no longer issue non-expiring access tokens.
            # An OSF PR (https://github.com/CenterForOpenScience/osf.io/pull/9935)
            # was merged on 05/09/2022 to address this issue.
            # Hence, there are many accounts without refresh tokens created before 05/09/2022 on production.
            # Access tokens issued prior to the change still works, and we should migrate them as is.
            self.check_fields(osf_account, ["oauth_key"])
            credentials = AccessTokenCredentials(access_token=osf_account.oauth_key)
        else:
            self.check_fields(osf_account, ["oauth_key"])
            credentials = AccessTokenCredentials(access_token=osf_account.oauth_key)
        return credentials

    def check_fields(self, osf_account: ExternalAccount, fields: list[str]):
        errors = []
        for field in fields:
            if getattr(osf_account, field, None) is None:
                error_string = f"Required field <<{field}>> is None"
                errors.append(error_string)
        if errors:
            raise CredentialException(errors)

    def get_api_base_url(self, external_service, osf_account):
        if external_service.wb_key == "owncloud":
            return f"{osf_account.profile_url.removesuffix('/')}/remote.php/dav/files/{quote_plus(osf_account.display_name)}/"
        elif external_service.wb_key == "gitlab":
            return f"{osf_account.oauth_secret.removesuffix('/')}"
        elif external_service.wb_key == "dataverse":
            return f"https://{osf_account.oauth_key}"
