from rest_framework_json_api import serializers
from rest_framework_json_api.relations import HyperlinkedRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.common import view_names
from addon_service.models import (
    AuthorizedCitationAccount,
    AuthorizedComputingAccount,
    AuthorizedStorageAccount,
    AuthorizedLinkAccount,
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

    authorized_citation_accounts = HyperlinkedRelatedField(
        many=True,
        queryset=AuthorizedCitationAccount.objects.all(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    authorized_computing_accounts = HyperlinkedRelatedField(
        many=True,
        queryset=AuthorizedComputingAccount.objects.all(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    authorized_link_accounts = HyperlinkedRelatedField(
        many=True,
        queryset=AuthorizedLinkAccount.objects.all(),
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
        "authorized_citation_accounts": (
            "addon_service.serializers.AuthorizedCitationAccountSerializer"
        ),
        "authorized_computing_accounts": (
            "addon_service.serializers.AuthorizedComputingAccountSerializer"
        ),
        "authorized_link_accounts": (
            "addon_service.serializers.AuthorizedLinkAccountSerializer"
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
            "authorized_citation_accounts",
            "authorized_computing_accounts",
            "authorized_link_accounts",
            "configured_resources",
        ]
