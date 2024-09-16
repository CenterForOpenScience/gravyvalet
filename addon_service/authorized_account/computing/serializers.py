from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    HyperlinkedRelatedField,
    ResourceRelatedField,
)
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.authorized_account.serializers import AuthorizedAccountSerializer
from addon_service.common import view_names
from addon_service.common.serializer_fields import (
    DataclassRelatedLinkField,
    ReadOnlyResourceRelatedField,
)
from addon_service.models import (
    AuthorizedComputingAccount,
    ConfiguredComputingAddon,
    ExternalComputingService,
    UserReference,
)


RESOURCE_TYPE = get_resource_type_from_model(AuthorizedComputingAccount)


class AuthorizedComputingAccountSerializer(AuthorizedAccountSerializer):
    external_computing_service = ResourceRelatedField(
        queryset=ExternalComputingService.objects.all(),
        many=False,
        source="external_service.externalcomputingservice",
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    configured_computing_addons = HyperlinkedRelatedField(
        many=True,
        queryset=ConfiguredComputingAddon.objects.active(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
        required=False,
    )
    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE), required=False
    )
    account_owner = ReadOnlyResourceRelatedField(
        many=False,
        queryset=UserReference.objects.all(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    authorized_operations = DataclassRelatedLinkField(
        dataclass_model=AddonOperationModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    included_serializers = {
        "account_owner": "addon_service.serializers.UserReferenceSerializer",
        "external_computing_service": "addon_service.serializers.ExternalComputingServiceSerializer",
        "configured_computing_addons": "addon_service.serializers.ConfiguredComputingAddonSerializer",
        "authorized_operations": "addon_service.serializers.AddonOperationSerializer",
    }

    class Meta:
        model = AuthorizedComputingAccount
        fields = [
            "id",
            "url",
            "display_name",
            "account_owner",
            "api_base_url",
            "auth_url",
            "authorized_capabilities",
            "authorized_operations",
            "authorized_operation_names",
            "configured_computing_addons",
            "credentials",
            "external_computing_service",
            "initiate_oauth",
            "credentials_available",
        ]
