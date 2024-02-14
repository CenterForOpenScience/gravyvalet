import factory
from factory.django import DjangoModelFactory

from addon_service import models as db
from app.settings import (
    AUTH_URI_ID,
    URI_ID,
)


class UserReferenceFactory(DjangoModelFactory):
    class Meta:
        model = db.UserReference

    user_uri = factory.Sequence(lambda n: f"{URI_ID}user{n}")


class ResourceReferenceFactory(DjangoModelFactory):
    class Meta:
        model = db.ResourceReference

    resource_uri = factory.Sequence(lambda n: f"{URI_ID}thing{n}")


class CredentialsIssuerFactory(DjangoModelFactory):
    class Meta:
        model = db.CredentialsIssuer


class ExternalCredentialsFactory(DjangoModelFactory):
    class Meta:
        model = db.ExternalCredentials


class ExternalAccountFactory(DjangoModelFactory):
    class Meta:
        model = db.ExternalAccount

    remote_account_id = factory.Faker("word")
    remote_account_display_name = factory.Faker("word")

    credentials_issuer = factory.SubFactory(CredentialsIssuerFactory)
    owner = factory.SubFactory(UserReferenceFactory)
    credentials = factory.SubFactory(ExternalCredentialsFactory)


###
# "Storage" models


class ExternalStorageServiceFactory(DjangoModelFactory):
    class Meta:
        model = db.ExternalStorageService

    max_concurrent_downloads = factory.Faker("pyint")
    max_upload_mb = factory.Faker("pyint")
    auth_uri = factory.Sequence(lambda n: f"{AUTH_URI_ID}{n}")
    credentials_issuer = factory.SubFactory(CredentialsIssuerFactory)


class AuthorizedStorageAccountFactory(DjangoModelFactory):
    class Meta:
        model = db.AuthorizedStorageAccount

    default_root_folder = "/"
    external_storage_service = factory.SubFactory(ExternalStorageServiceFactory)
    external_account = factory.SubFactory(ExternalAccountFactory)
    # TODO: external_account.credentials_issuer same as
    #       external_storage_service.credentials_issuer


class ConfiguredStorageAddonFactory(DjangoModelFactory):
    class Meta:
        model = db.ConfiguredStorageAddon

    root_folder = "/"
    base_account = factory.SubFactory(AuthorizedStorageAccountFactory)
    authorized_resource = factory.SubFactory(ResourceReferenceFactory)
