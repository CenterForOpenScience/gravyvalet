from rest_framework_json_api import serializers

from addon_service.common.enum_serializers import EnumNameMultipleChoiceField
from addon_toolkit import AddonCapabilities


REQUIRED_FIELDS = frozenset(["url", "connected_operations", "authorized_resource"])


class ConfiguredAddonSerializer(serializers.HyperlinkedModelSerializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not REQUIRED_FIELDS.issubset(set(self.fields.keys())):
            raise Exception(
                f"{self.__class__.__name__} requires {self.REQUIRED_FIELDS} to be instantiated"
            )

    connected_capabilities = EnumNameMultipleChoiceField(enum_cls=AddonCapabilities)
    connected_operation_names = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    display_name = serializers.CharField(
        allow_blank=True, allow_null=True, required=False, max_length=256
    )

    authorized_resource_uri = serializers.CharField(
        required=False, source="resource_uri", write_only=True
    )

    class Meta:
        fields = [
            "id",
            "url",
            "display_name",
            "base_account",
            "authorized_resource",
            "authorized_resource_uri",
            "connected_capabilities",
            "connected_operations",
            "connected_operation_names",
        ]
