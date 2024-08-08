from rest_framework_json_api import serializers
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common import view_names
from addon_service.common.serializer_fields import DataclassRelatedLinkField

from .models import AddonImpModel


RESOURCE_TYPE = get_resource_type_from_model(AddonImpModel)


class AddonImpSerializer(serializers.Serializer):
    """api serializer for the `AddonImpModel` model"""

    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE)
    )
    name = serializers.CharField(read_only=True)
    docstring = serializers.CharField(read_only=True, source="imp_docstring")
    interface_docstring = serializers.CharField(read_only=True)

    implemented_operations = DataclassRelatedLinkField(
        dataclass_model=AddonOperationModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    included_serializers = {
        "implemented_operations": "addon_service.serializers.AddonOperationSerializer",
    }

    class Meta:
        model = AddonImpModel
        fields = [
            "url",
            "name",
            "docstring",
            "implemented_operations",
        ]
