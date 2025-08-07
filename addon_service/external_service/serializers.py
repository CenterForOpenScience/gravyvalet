from rest_framework_json_api import serializers

from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.enum_serializers import EnumNameChoiceField
from addon_service.external_service.models import ExternalService


REQUIRED_FIELDS = frozenset(["url", "addon_imp"])


class ExternalServiceSerializer(serializers.HyperlinkedModelSerializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Check whether subclasses declare all of required fields
        if not REQUIRED_FIELDS.issubset(set(self.fields.keys())):
            raise Exception(
                f"{self.__class__.__name__} requires {self.REQUIRED_FIELDS} to be instantiated"
            )

    credentials_format = EnumNameChoiceField(
        enum_cls=CredentialsFormats,
        read_only=True,
    )
    icon_url = serializers.SerializerMethodField()

    def get_icon_url(self, obj: ExternalService):
        request = self.context.get("request")
        if request and obj.icon_url:
            return request.build_absolute_uri(obj.icon_url)
        return None

    external_service_name = serializers.CharField(read_only=True)
    api_base_url_options = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )

    included_serializers = {
        "addon_imp": "addon_service.serializers.AddonImpSerializer",
    }

    class Meta:
        model = ExternalService
        resource_name = "external-services"
        fields = [
            "id",
            "addon_imp",
            "auth_uri",
            "credentials_format",
            "max_concurrent_downloads",
            "max_upload_mb",
            "display_name",
            "url",
            "wb_key",
            "external_service_name",
            "icon_url",
            "api_base_url_options",
        ]
