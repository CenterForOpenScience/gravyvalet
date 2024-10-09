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
    AuthorizedCitationAccount,
    ConfiguredCitationAddon,
    ExternalCitationService,
    UserReference,
)


RESOURCE_TYPE = get_resource_type_from_model(AuthorizedCitationAccount)


class AuthorizedCitationAccountSerializer(AuthorizedAccountSerializer):
    external_citation_service = ResourceRelatedField(
        queryset=ExternalCitationService.objects.all(),
        many=False,
        source="external_service",
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    configured_citation_addons = HyperlinkedRelatedField(
        many=True,
        queryset=ConfiguredCitationAddon.objects.active(),
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
        "external_citation_service": "addon_service.serializers.ExternalCitationServiceSerializer",
        "configured_citation_addons": "addon_service.serializers.ConfiguredCitationAddonSerializer",
        "authorized_operations": "addon_service.serializers.AddonOperationSerializer",
    }

    class Meta:
        model = AuthorizedCitationAccount
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
            "configured_citation_addons",
            "credentials",
            "default_root_folder",
            "external_citation_service",
            "initiate_oauth",
            "credentials_available",
        ]
