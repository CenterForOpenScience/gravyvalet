import factory
from django.conf import settings
from factory.django import DjangoModelFactory

from addon_service import models as db
from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.known_imps import AddonRegistry
from addon_service.common.service_types import ServiceTypes
from addon_service.external_service.storage.models import StorageSupportedFeatures
from addon_toolkit import AddonCapabilities

from ._helpers import patch_encryption_key_derivation


class UserReferenceFactory(DjangoModelFactory):
    class Meta:
        model = db.UserReference

    user_uri = factory.Sequence(lambda n: f"{settings.OSF_BASE_URL}/user{n}")


class ResourceReferenceFactory(DjangoModelFactory):
    class Meta:
        model = db.ResourceReference

    resource_uri = factory.Sequence(lambda n: f"{settings.OSF_BASE_URL}/thing{n}")


class OAuth2ClientConfigFactory(DjangoModelFactory):
    class Meta:
        model = db.OAuth2ClientConfig

    auth_uri = factory.Sequence(lambda n: f"https://api.example/auth/{n}")
    auth_callback_url = "https://osf.example/auth/callback"
    token_endpoint_url = "https://api.example.com/oauth/token"
    client_id = factory.Faker("word")
    client_secret = factory.Faker("word")


class OAuth1ClientConfigFactory(DjangoModelFactory):
    class Meta:
        model = db.OAuth1ClientConfig

    auth_url = "https://api.example/auth/"
    auth_callback_url = "https://api.example/auth/"
    access_token_url = "https://osf.example/oauth/access"
    request_token_url = "https://api.example.com/oauth/request"
    client_key = factory.Faker("word")
    client_secret = factory.Faker("word")


class AddonOperationInvocationFactory(DjangoModelFactory):
    class Meta:
        model = db.AddonOperationInvocation

    operation_identifier = "STORAGE:get_item_info"
    operation_kwargs = {"item_id": "foo"}
    thru_account = factory.SubFactory(
        "addon_service.tests._factories.AuthorizedStorageAccountFactory"
    )
    thru_addon = factory.SubFactory(
        "addon_service.tests._factories.ConfiguredStorageAddonFactory",
        base_account=factory.SelfAttribute("..thru_account"),
    )
    by_user = factory.SubFactory(UserReferenceFactory)


###
# "Storage" models


class ExternalStorageServiceFactory(DjangoModelFactory):
    class Meta:
        model = db.ExternalStorageService

    display_name = factory.Faker("word")
    max_concurrent_downloads = factory.Faker("pyint")
    max_upload_mb = factory.Faker("pyint")
    int_addon_imp = AddonRegistry.get_imp_number(AddonRegistry.get_imp_by_name("BLARG"))
    supported_scopes = ["service.url/grant_all"]

    @classmethod
    def _create(
        cls,
        model_class,
        credentials_format=CredentialsFormats.PERSONAL_ACCESS_TOKEN,
        service_type=ServiceTypes.PUBLIC,
        supported_features=StorageSupportedFeatures.ADD_UPDATE_FILES,
        *args,
        **kwargs,
    ):
        api_base_url = ""
        if ServiceTypes.PUBLIC in service_type:
            api_base_url = "https://api.example.url/v1"
        return super()._create(
            model_class=model_class,
            int_credentials_format=credentials_format.value,
            int_service_type=service_type.value,
            int_supported_features=supported_features.value,
            api_base_url=api_base_url,
            *args,
            **kwargs,
        )


class ExternalStorageOAuth2ServiceFactory(ExternalStorageServiceFactory):
    credentials_format = CredentialsFormats.OAUTH2
    oauth2_client_config = factory.SubFactory(OAuth2ClientConfigFactory)


class ExternalStorageOAuth1ServiceFactory(ExternalStorageServiceFactory):
    credentials_format = CredentialsFormats.OAUTH1A
    oauth1_client_config = factory.SubFactory(OAuth1ClientConfigFactory)


class AuthorizedStorageAccountFactory(DjangoModelFactory):
    class Meta:
        model = db.AuthorizedStorageAccount

    display_name = factory.Faker("word")
    default_root_folder = "/"
    authorized_capabilities = AddonCapabilities.ACCESS | AddonCapabilities.UPDATE

    @classmethod
    def _create(
        cls,
        model_class,
        account_owner=None,
        external_service=None,
        credentials=None,
        credentials_format=CredentialsFormats.OAUTH2,
        authorized_scopes=None,
        *args,
        **kwargs,
    ):
        account = super()._create(
            model_class=model_class,
            external_service=external_service
            or ExternalStorageOAuth2ServiceFactory(
                credentials_format=credentials_format
            ),
            account_owner=account_owner or UserReferenceFactory(),
            *args,
            **kwargs,
        )
        if credentials_format is CredentialsFormats.OAUTH2:
            account.initiate_oauth2_flow(authorized_scopes)
        else:
            with patch_encryption_key_derivation():
                account.credentials = credentials
            account.save()
        return account


class ConfiguredStorageAddonFactory(DjangoModelFactory):
    class Meta:
        model = db.ConfiguredStorageAddon

    root_folder = "/"
    connected_capabilities = AddonCapabilities.ACCESS

    @classmethod
    def _create(
        cls,
        model_class,
        authorized_resource=None,
        external_storage_service=None,
        credentials_format=CredentialsFormats.OAUTH2,
        base_account=None,
        account_owner=None,
        credentials=None,
        *args,
        **kwargs,
    ):
        authorized_resource = authorized_resource or ResourceReferenceFactory()
        base_account = base_account or AuthorizedStorageAccountFactory(
            external_service=external_storage_service,
            credentials_format=credentials_format,
            account_owner=account_owner,
            credentials=credentials,
        )

        return super()._create(
            model_class=model_class,
            authorized_resource=authorized_resource,
            base_account=base_account,
            *args,
            **kwargs,
        )


###
# "Link" models


class ExternalLinkServiceFactory(DjangoModelFactory):
    class Meta:
        model = db.ExternalLinkService

    display_name = factory.Faker("word")
    int_addon_imp = AddonRegistry.get_imp_number(
        AddonRegistry.get_imp_by_name("LINK_DATAVERSE")
    )
    supported_scopes = ["service.url/grant_all"]

    @classmethod
    def _create(
        cls,
        model_class,
        credentials_format=CredentialsFormats.PERSONAL_ACCESS_TOKEN,
        service_type=ServiceTypes.PUBLIC,
        supported_resource_types=None,
        supported_features=None,
        *args,
        **kwargs,
    ):
        from addon_service.external_service.link.models import LinkSupportedFeatures
        from addon_toolkit.interfaces.link import SupportedResourceTypes

        api_base_url = ""
        if ServiceTypes.PUBLIC in service_type:
            api_base_url = "https://api.example.url/v1"

        supported_resource_types = (
            supported_resource_types or SupportedResourceTypes.Other
        )

        supported_features = (
            supported_features or LinkSupportedFeatures.ADD_UPDATE_FILES
        )

        return super()._create(
            model_class=model_class,
            int_credentials_format=credentials_format.value,
            int_service_type=service_type.value,
            int_supported_resource_types=supported_resource_types.value,
            int_supported_features=supported_features.value,
            api_base_url=api_base_url,
            *args,
            **kwargs,
        )


class ExternalLinkOAuth2ServiceFactory(ExternalLinkServiceFactory):
    credentials_format = CredentialsFormats.OAUTH2
    oauth2_client_config = factory.SubFactory(OAuth2ClientConfigFactory)


class ExternalLinkOAuth1ServiceFactory(ExternalLinkServiceFactory):
    credentials_format = CredentialsFormats.OAUTH1A
    oauth1_client_config = factory.SubFactory(OAuth1ClientConfigFactory)


class AuthorizedLinkAccountFactory(DjangoModelFactory):
    class Meta:
        model = db.AuthorizedLinkAccount

    display_name = factory.Faker("word")
    authorized_capabilities = AddonCapabilities.ACCESS | AddonCapabilities.UPDATE

    @classmethod
    def _create(
        cls,
        model_class,
        account_owner=None,
        external_service=None,
        credentials=None,
        credentials_format=CredentialsFormats.OAUTH2,
        authorized_scopes=None,
        *args,
        **kwargs,
    ):
        from addon_service.tests._helpers import patch_encryption_key_derivation

        account = super()._create(
            model_class=model_class,
            external_service=external_service
            or ExternalLinkOAuth2ServiceFactory(credentials_format=credentials_format),
            account_owner=account_owner or UserReferenceFactory(),
            *args,
            **kwargs,
        )
        if credentials_format is CredentialsFormats.OAUTH2:
            account.initiate_oauth2_flow(authorized_scopes)
        else:
            with patch_encryption_key_derivation():
                from addon_service.tests.test_by_type.test_authorized_link_account import (
                    MOCK_CREDENTIALS,
                )

                account.credentials = credentials or MOCK_CREDENTIALS.get(
                    credentials_format
                )
            account.save()
        return account


class ConfiguredLinkAddonFactory(DjangoModelFactory):
    class Meta:
        model = db.ConfiguredLinkAddon

    target_id = factory.Faker("uuid4")
    connected_capabilities = AddonCapabilities.ACCESS

    @classmethod
    def _create(
        cls,
        model_class,
        authorized_resource=None,
        external_link_service=None,
        credentials_format=CredentialsFormats.OAUTH2,
        base_account=None,
        account_owner=None,
        credentials=None,
        resource_type=None,
        *args,
        **kwargs,
    ):
        from addon_toolkit.interfaces.link import SupportedResourceTypes

        authorized_resource = authorized_resource or ResourceReferenceFactory()
        base_account = base_account or AuthorizedLinkAccountFactory(
            external_service=external_link_service,
            credentials_format=credentials_format,
            account_owner=account_owner,
            credentials=credentials,
        )

        resource_type = resource_type or SupportedResourceTypes.Other

        kwargs["int_resource_type"] = resource_type.value

        addon = super()._create(
            model_class=model_class,
            authorized_resource=authorized_resource,
            base_account=base_account,
            *args,
            **kwargs,
        )

        return addon
