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
    """
    Serializer for AuthorizedStorageAccount.
    """
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
        "external_storage_service": "addon_service.serializers.ExternalStorageServiceSerializer",
        "configured_storage_addons": "addon_service.serializers.ConfiguredStorageAddonSerializer",
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
    """
    POST Serializer for AuthorizedStorageAccount.
    """
    external_storage_service = ResourceRelatedField(
        queryset=ExternalStorageService.objects.all(),
        many=False,
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    account_owner = ResourceRelatedField(
        many=False,
        queryset=InternalUser.objects.all(),
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)

    def create(self, validated_data):
        """
        Create method for AuthorizedStorageAccount.
        """
        external_storage_service = validated_data["external_storage_service"]
        internal_user = validated_data["account_owner"]

        external_credentials, created = ExternalCredentials.objects.get_or_create(
            oauth_key=validated_data['username'],
            oauth_secret=validated_data['password'],
        )

        external_account, created = ExternalAccount.objects.get_or_create(
            owner=internal_user,
            credentials=external_credentials,
            credentials_issuer=external_storage_service.credentials_issuer,
        )
        return super().create(
            {
                "external_storage_service": external_storage_service,
                "external_account": external_account,
            }
        )

    class Meta:
        model = AuthorizedStorageAccount
        fields = [
            "external_storage_service",
            "username",
            "password",
            "account_owner"
        ]
