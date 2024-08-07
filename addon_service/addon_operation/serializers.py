from rest_framework_json_api import serializers
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_imp.models import AddonImpModel
from addon_service.common import view_names
from addon_service.common.enum_serializers import EnumNameChoiceField
from addon_service.common.serializer_fields import DataclassRelatedDataField
from addon_toolkit import AddonCapabilities

from .models import AddonOperationModel


RESOURCE_TYPE = get_resource_type_from_model(AddonOperationModel)


class AddonOperationSerializer(serializers.Serializer):
    """api serializer for the `AddonOperationModel` model"""

    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE)
    )

    ###
    # attributes

    name = serializers.CharField(read_only=True)
    docstring = serializers.CharField(read_only=True)
    capability = EnumNameChoiceField(enum_cls=AddonCapabilities, read_only=True)
    kwargs_jsonschema = serializers.JSONField(read_only=True)
    result_jsonschema = serializers.JSONField(read_only=True)

    ###
    # relationships

    implemented_by = DataclassRelatedDataField(
        dataclass_model=AddonImpModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
        read_only=True,
        many=True,
    )

    ###
    # wiring

    included_serializers = {
        "implemented_by": "addon_service.serializers.AddonImpSerializer",
    }

    class Meta:
        model = AddonOperationModel
        fields = [
            "id",
            "name",
            "docstring",
            "capability",
            "kwargs_jsonschema",
            "result_jsonschema",
        ]
