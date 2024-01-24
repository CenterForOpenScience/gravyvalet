from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    HyperlinkedRelatedField,
    ResourceRelatedField,
)
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.models import (
    AuthorizedStorageAccount,
    ConfiguredStorageAddon,
    ExternalAccount,
    ExternalCredentials,
    ExternalStorageService,
    InternalUser,
)


RESOURCE_NAME = get_resource_type_from_model(AuthorizedStorageAccount)


class AuthorizedStorageAccountSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=f"{RESOURCE_NAME}-detail")
    account_owner = HyperlinkedRelatedField(
        many=False,
        queryset=InternalUser.objects.all(),
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    external_storage_service = ResourceRelatedField(
        queryset=ExternalStorageService.objects.all(),
        many=False,
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    configured_storage_addons = HyperlinkedRelatedField(
        many=True,
        queryset=ConfiguredStorageAddon.objects.all(),
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )

    included_serializers = {
        "account_owner": "addon_service.serializers.InternalUserSerializer",
        "external_storage_service": (
            "addon_service.serializers.ExternalStorageServiceSerializer"
        ),
        "configured_storage_addons": (
            "addon_service.serializers.ConfiguredStorageAddonSerializer"
        ),
    }

    class Meta:
        model = AuthorizedStorageAccount
        fields = [
            "url",
            "account_owner",
            "configured_storage_addons",
            "default_root_folder",
            "external_storage_service",
        ]


class AuthorizedStorageAccountPOSTSerializer(serializers.HyperlinkedModelSerializer):
    external_storage_service = ResourceRelatedField(
        queryset=ExternalStorageService.objects.all(),
        many=False,
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    url = serializers.CharField(write_only=True, required=False)
    repo = serializers.CharField(write_only=True, required=False)
    access_key = serializers.CharField(write_only=True, required=False)
    secret_key = serializers.CharField(write_only=True, required=False)

    def get_internal_user_from_request_or_callback(self):
        #  TODO: Write real code to get user from auth backend
        return InternalUser.objects.get(
            id=self.context["request"].GET["placeholder-auth"]  # Placeholder
        )

    def validate_credentials_using_issuer_or_error(self, external_storage_service, credentials):
        credentials_issuer = external_storage_service.credentials_issuer

        # TODO: Write real issuer_check
        if credentials_issuer.check_credentials(credentials):
            return ExternalCredentials.objects.create(
                **credentials_issuer.coerce_credentials_into_db_terms(credentials)
            )
        else:
            raise Exception(
                "placeholder for failure of validate_credentials_using_issuer_or_error"
            )

    def create(self, validated_data):
        external_storage_service = validated_data["external_storage_service"]
        credentials = external_storage_service.credentials_issuer.retrieve_credentials(
            validated_data
        )

        # TODO: Get user data from OSF
        internal_user = self.get_internal_user_from_request_or_callback()

        # TODO: Write CredentialIssuer code to check if valid with external service
        external_credentials = self.validate_credentials_using_issuer_or_error(
            external_storage_service,
            credentials
        )

        external_account, created = ExternalAccount.objects.get_or_create(
            owner=internal_user,
            credentials=external_credentials,
            # TODO: credentials_issuer comes from here?
            credentials_issuer=external_storage_service.credentials_issuer,
        )
        return super().create(
            dict(
                external_storage_service=external_storage_service,
                external_account=external_account,
            )
        )

    class Meta:
        model = AuthorizedStorageAccount
        fields = [
            "external_storage_service",
            "username",
            "password",
            "repo",
            "url",
            "access_key",
            "secret_key",
        ]
