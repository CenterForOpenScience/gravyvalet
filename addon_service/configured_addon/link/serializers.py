from rest_framework.fields import (
    CharField,
    URLField,
)
from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common import view_names
from addon_service.common.enum_serializers import EnumNameChoiceField
from addon_service.common.serializer_fields import DataclassRelatedLinkField
from addon_service.configured_addon.serializers import ConfiguredAddonSerializer
from addon_service.external_service.link.models import ExternalLinkService
from addon_service.models import (
    AuthorizedLinkAccount,
    ConfiguredLinkAddon,
)
from addon_toolkit.interfaces.link import SupportedResourceTypes


RESOURCE_TYPE = get_resource_type_from_model(ConfiguredLinkAddon)


class ConfiguredLinkAddonSerializer(ConfiguredAddonSerializer):
    """api serializer for the `ConfiguredLinkAddon` model"""

    target_url = URLField(read_only=True)
    target_id = CharField(required=False, allow_null=True)
    resource_type = EnumNameChoiceField(
        required=False,
        allow_null=True,
        enum_cls=SupportedResourceTypes,
    )

    connected_operations = DataclassRelatedLinkField(
        dataclass_model=AddonOperationModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
        read_only=True,
    )
    base_account = ResourceRelatedField(
        queryset=AuthorizedLinkAccount.objects.all(),
        many=False,
        source="base_account.authorizedlinkaccount",
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    external_link_service = ResourceRelatedField(
        many=False,
        read_only=True,
        model=ExternalLinkService,
        source="base_account.external_service.externallinkservice",
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    authorized_resource = ResourceRelatedField(
        many=False,
        read_only=True,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    included_serializers = {
        "base_account": "addon_service.serializers.AuthorizedLinkAccountSerializer",
        "external_link_service": "addon_service.serializers.ExternalLinkServiceSerializer",
        "authorized_resource": "addon_service.serializers.ResourceReferenceSerializer",
        "connected_operations": "addon_service.serializers.AddonOperationSerializer",
    }

    class Meta:
        model = ConfiguredLinkAddon
        read_only_fields = ["external_link_service"]
        one_addon_per_node = False
        fields = [
            "id",
            "display_name",
            "target_url",
            "base_account",
            "authorized_resource",
            "authorized_resource_uri",
            "connected_capabilities",
            "connected_operations",
            "connected_operation_names",
            "external_link_service",
            "current_user_is_owner",
            "external_service_name",
            "resource_type",
            "target_id",
        ]


class VerifiedLinkSerializer(serializers.Serializer):
    """Serialize ConfiguredLinkAddon information required by OSF.

    The information is shaped for osf to be able to update datacite and share metadata
    with minimal performance footprint
    """

    class JSONAPIMeta:
        resource_name = "verified-link"

    target_url = URLField(read_only=True)
    target_id = CharField(read_only=True)
    resource_type = EnumNameChoiceField(read_only=True, enum_cls=SupportedResourceTypes)
    service_name = CharField(
        read_only=True, source="external_service.external_service_name"
    )
