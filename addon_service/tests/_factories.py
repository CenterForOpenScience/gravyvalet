import factory
from django.conf import settings
from factory.django import DjangoModelFactory

from addon_service import models as db
from addon_service.addon_imp.known import get_imp_by_name
from addon_toolkit import AddonCapabilities


class UserReferenceFactory(DjangoModelFactory):
    class Meta:
        model = db.UserReference

    user_uri = factory.Sequence(lambda n: f"{settings.URI_ID}user{n}")


class ResourceReferenceFactory(DjangoModelFactory):
    class Meta:
        model = db.ResourceReference

    resource_uri = factory.Sequence(lambda n: f"{settings.URI_ID}thing{n}")


class CredentialsIssuerFactory(DjangoModelFactory):
    class Meta:
        model = db.CredentialsIssuer

    name = factory.Faker("word")


class ExternalCredentialsFactory(DjangoModelFactory):
    class Meta:
        model = db.ExternalCredentials


class ExternalAccountFactory(DjangoModelFactory):
    class Meta:
        model = db.ExternalAccount

    credentials_issuer = factory.SubFactory(CredentialsIssuerFactory)
    owner = factory.SubFactory(UserReferenceFactory)
    credentials = factory.SubFactory(ExternalCredentialsFactory)


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

    max_concurrent_downloads = factory.Faker("pyint")
    max_upload_mb = factory.Faker("pyint")
    auth_uri = factory.Sequence(lambda n: f"{settings.AUTH_URI_ID}{n}")
    callback_url = "https://osf.io/auth/callback"
    credentials_issuer = factory.SubFactory(CredentialsIssuerFactory)
    int_addon_imp = get_imp_by_name("BLARG").imp_number


class AuthorizedStorageAccountFactory(DjangoModelFactory):
    class Meta:
        model = db.AuthorizedStorageAccount

    default_root_folder = "/"
    authorized_capabilities = factory.List([AddonCapabilities.ACCESS])
    external_storage_service = factory.SubFactory(ExternalStorageServiceFactory)
    external_account = factory.SubFactory(ExternalAccountFactory)
    # TODO: external_account.credentials_issuer same as
    #       external_storage_service.credentials_issuer


class ConfiguredStorageAddonFactory(DjangoModelFactory):
    class Meta:
        model = db.ConfiguredStorageAddon

    root_folder = "/"
    connected_capabilities = factory.List([AddonCapabilities.ACCESS])
    base_account = factory.SubFactory(AuthorizedStorageAccountFactory)
    authorized_resource = factory.SubFactory(ResourceReferenceFactory)
