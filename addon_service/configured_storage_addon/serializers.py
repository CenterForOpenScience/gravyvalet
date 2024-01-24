from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.models import (
    AuthorizedStorageAccount,
    ConfiguredStorageAddon,
    InternalResource,
)


RESOURCE_NAME = get_resource_type_from_model(ConfiguredStorageAddon)


class ConfiguredStorageAddonSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=f"{RESOURCE_NAME}-detail")
    base_account = ResourceRelatedField(
        queryset=AuthorizedStorageAccount.objects.all(),
        many=False,
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    authorized_resource = ResourceRelatedField(
        queryset=InternalResource.objects.all(),
        many=False,
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )

    included_serializers = {
        "base_account": (
            "addon_service.serializers.AuthorizedStorageAccountSerializer"
        ),
        "authorized_resource": "addon_service.serializers.InternalResourceSerializer",
    }

    class Meta:
        model = ConfiguredStorageAddon
        fields = [
            "url",
            "root_folder",
            "base_account",
            "authorized_resource",
        ]


class ConfiguredStorageAddonPOSTSerializer(serializers.HyperlinkedModelSerializer):
    base_account = ResourceRelatedField(
        queryset=AuthorizedStorageAccount.objects.all(),
        many=False,
        related_link_view_name=f"{RESOURCE_NAME}-related",
    )
    guid = serializers.CharField(write_only=True)

    def get_authorized_resource(self, guid):
        """
        Make request to OSF
        """
        # TODO: Write real code to request InternalResource info from OSF
        return InternalResource.objects.create(resource_uri=guid)

    def create(self, validated_data):
        base_account = validated_data["base_account"]
        guid = validated_data["guid"]
        authorized_resource = self.get_authorized_resource(guid)
        return super().create(
            dict(base_account=base_account, authorized_resource=authorized_resource)
        )

    class Meta:
        model = ConfiguredStorageAddon
        fields = ["base_account", "guid"]
