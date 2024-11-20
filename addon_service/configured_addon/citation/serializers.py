from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.authorized_account.citation.models import AuthorizedCitationAccount
from addon_service.common import view_names
from addon_service.common.serializer_fields import DataclassRelatedLinkField
from addon_service.configured_addon.citation.models import ConfiguredCitationAddon
from addon_service.configured_addon.serializers import ConfiguredAddonSerializer
from addon_service.external_service.citation.models import ExternalCitationService


RESOURCE_TYPE = get_resource_type_from_model(ConfiguredCitationAddon)


class ConfiguredCitationAddonSerializer(ConfiguredAddonSerializer):
    """api serializer for the `ConfiguredCitationAddon` model"""

    root_folder = serializers.CharField(required=False, allow_blank=True)
    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE)
    )
    connected_operations = DataclassRelatedLinkField(
        dataclass_model=AddonOperationModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
        read_only=True,
    )
    base_account = ResourceRelatedField(
        queryset=AuthorizedCitationAccount.objects.all(),
        many=False,
        source="base_account.authorizedcitationaccount",
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    external_citation_service = ResourceRelatedField(
        many=False,
        read_only=True,
        model=ExternalCitationService,
        source="base_account.external_service.externalstorageservice",
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    authorized_resource = ResourceRelatedField(
        many=False,
        read_only=True,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    included_serializers = {
        "base_account": (
            "addon_service.serializers.AuthorizedCitationAccountSerializer"
        ),
        "external_citation_service": "addon_service.serializers.ExternalCitationServiceSerializer",
        "authorized_resource": "addon_service.serializers.ResourceReferenceSerializer",
        "connected_operations": "addon_service.serializers.AddonOperationSerializer",
    }

    class Meta:
        model = ConfiguredCitationAddon
        fields = [
            "id",
            "url",
            "display_name",
            "root_folder",
            "base_account",
            "authorized_resource",
            "authorized_resource_uri",
            "connected_capabilities",
            "connected_operations",
            "connected_operation_names",
        ]
