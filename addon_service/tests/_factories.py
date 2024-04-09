import factory
from django.conf import settings
from factory.django import DjangoModelFactory

from addon_service import models as db
from addon_service.addon_imp.known import get_imp_by_name
from addon_service.credentials import CredentialsFormats
from addon_toolkit import AddonCapabilities


class UserReferenceFactory(DjangoModelFactory):
    class Meta:
        model = db.UserReference

    user_uri = factory.Sequence(lambda n: f"{settings.URI_ID}user{n}")


class ResourceReferenceFactory(DjangoModelFactory):
    class Meta:
        model = db.ResourceReference

    resource_uri = factory.Sequence(lambda n: f"{settings.URI_ID}thing{n}")


class OAuth2ClientConfigFactory(DjangoModelFactory):
    class Meta:
        model = db.OAuth2ClientConfig

    auth_uri = factory.Sequence(lambda n: f"{settings.AUTH_URI_ID}{n}")
    client_id = factory.Faker("word")


class AddonOperationInvocationFactory(DjangoModelFactory):
    class Meta:
        model = db.AddonOperationInvocation

    operation_identifier = "BLARG:download"
    operation_kwargs = {"item_id": "foo"}
    thru_addon = factory.SubFactory(
        "addon_service.tests._factories.ConfiguredStorageAddonFactory"
    )
    by_user = factory.SubFactory(UserReferenceFactory)


###
# "Storage" models


class ExternalStorageServiceFactory(DjangoModelFactory):
    class Meta:
        model = db.ExternalStorageService

    service_name = factory.Faker("word")
    max_concurrent_downloads = factory.Faker("pyint")
    max_upload_mb = factory.Faker("pyint")
    auth_callback_url = "https://osf.io/auth/callback"
    int_addon_imp = get_imp_by_name("BLARG").imp_number
    oauth2_client_config = factory.SubFactory(OAuth2ClientConfigFactory)
    supported_scopes = ["service.url/grant_all"]

    @classmethod
    def _create(cls, model_class, credentials_format=None, *args, **kwargs):
        int_credentials_format = (
            credentials_format.value
            if credentials_format
            else CredentialsFormats.OAUTH2.value
        )
        return super()._create(
            model_class=model_class,
            int_credentials_format=int_credentials_format,
            *args,
            **kwargs,
        )


class AuthorizedStorageAccountFactory(DjangoModelFactory):
    class Meta:
        model = db.AuthorizedStorageAccount

    default_root_folder = "/"
    authorized_capabilities = factory.List([AddonCapabilities.ACCESS])

    @classmethod
    def _create(
        cls,
        model_class,
        external_storage_service=None,
        account_owner=None,
        credentials_dict=None,
        credentials_format=CredentialsFormats.OAUTH2,
        authorized_scopes=None,
        *args,
        **kwargs,
    ):
        account = super()._create(
            model_class=model_class,
            external_storage_service=external_storage_service
            or ExternalStorageServiceFactory(credentials_format=credentials_format),
            account_owner=account_owner or UserReferenceFactory(),
            *args,
            **kwargs,
        )
        if credentials_format is CredentialsFormats.OAUTH2:
            account.initiate_oauth2_flow(authorized_scopes)
        else:
            account.set_credentials(credentials_dict)
        return account


class ConfiguredStorageAddonFactory(DjangoModelFactory):
    class Meta:
        model = db.ConfiguredStorageAddon

    root_folder = "/"
    connected_capabilities = factory.List([AddonCapabilities.ACCESS])
    base_account = factory.SubFactory(AuthorizedStorageAccountFactory)
    authorized_resource = factory.SubFactory(ResourceReferenceFactory)
