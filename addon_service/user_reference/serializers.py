from rest_framework_json_api import serializers
from rest_framework_json_api.relations import HyperlinkedRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.common import view_names
from addon_service.models import (
    AuthorizedStorageAccount,
    ResourceReference,
    UserReference,
)


RESOURCE_TYPE = get_resource_type_from_model(UserReference)


class UserReferenceSerializer(serializers.HyperlinkedModelSerializer):
    """api serializer for the `UserReference` model"""

    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE)
    )

    authorized_storage_accounts = HyperlinkedRelatedField(
        many=True,
        queryset=AuthorizedStorageAccount.objects.all(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    configured_resources = HyperlinkedRelatedField(
        many=True,
        queryset=ResourceReference.objects.all(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    included_serializers = {
        "authorized_storage_accounts": (
            "addon_service.serializers.AuthorizedStorageAccountSerializer"
        ),
        "configured_resources": (
            "addon_service.serializers.ResourceReferenceSerializer"
        ),
    }

    class Meta:
        model = UserReference
        fields = [
            "id",
            "url",
            "user_uri",
            "authorized_storage_accounts",
            "configured_resources",
        ]
