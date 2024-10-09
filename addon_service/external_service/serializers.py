from rest_framework_json_api import serializers

from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.common.enum_serializers import EnumNameChoiceField


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

    included_serializers = {
        "addon_imp": "addon_service.serializers.AddonImpSerializer",
    }

    class Meta:
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
        ]
