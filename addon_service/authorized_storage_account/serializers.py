from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    HyperlinkedRelatedField,
    ResourceRelatedField,
)
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.models import (
    AuthorizedStorageAccount,
    ExternalStorageService,
    InternalUser,
)


RESOURCE_NAME = get_resource_type_from_model(AuthorizedStorageAccount)


class ReadAuthorizedStorageAccountSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=f"{RESOURCE_NAME}-detail")
    account_owner = HyperlinkedRelatedField(
        many=False,
        read_only=True,
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    external_storage_service = ResourceRelatedField(
        many=False,
        read_only=True,
        queryset=ExternalStorageService.objects.all(),
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    configured_storage_addons = HyperlinkedRelatedField(
        many=True,
        read_only=True,
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


class WriteAuthorizedStorageAccountSerializer(serializers.HyperlinkedModelSerializer):
    account_owner = HyperlinkedRelatedField(
        many=False,
        queryset=InternalUser.objects.all(),
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    external_storage_service = ResourceRelatedField(
        many=False,
        queryset=ExternalStorageService.objects.all(),
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    # credentials, in-line as fields

    included_serializers = {
        "account_owner": "addon_service.serializers.InternalUserSerializer",
        "external_storage_service": (
            "addon_service.serializers.ExternalStorageServiceSerializer"
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

    def create(self, validated_data):
        # implicitly create ExternalAccount
        # depending on
        _resp = super().create(validated_data)
        return _resp
