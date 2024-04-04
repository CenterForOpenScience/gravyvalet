from secrets import token_urlsafe

from rest_framework_json_api import serializers
from rest_framework_json_api.relations import (
    HyperlinkedRelatedField,
    ResourceRelatedField,
)
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.addon_operation.models import AddonOperationModel
from addon_service.common import view_names
from addon_service.common.enums.serializers import EnumNameMultipleChoiceField
from addon_service.common.serializer_fields import (
    DataclassRelatedLinkField,
    ReadOnlyResourceRelatedField,
)
from addon_service.models import (
    AuthorizedStorageAccount,
    ConfiguredStorageAddon,
    ExternalAccount,
    ExternalCredentials,
    ExternalStorageService,
    UserReference,
)
from addon_toolkit import AddonCapabilities


RESOURCE_TYPE = get_resource_type_from_model(AuthorizedStorageAccount)


class AuthorizedStorageAccountSerializer(serializers.HyperlinkedModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Check if it's a POST request and remove the field as it's not in our FE spec
        if "context" in kwargs and kwargs["context"]["request"].method == "POST":
            self.fields.pop("configured_storage_addons", None)

    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE), required=False
    )
    authorized_capabilities = EnumNameMultipleChoiceField(enum_cls=AddonCapabilities)
    authorized_operation_names = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    auth_url = serializers.CharField(read_only=True)
    account_owner = ReadOnlyResourceRelatedField(
        many=False,
        queryset=UserReference.objects.all(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    external_storage_service = ResourceRelatedField(
        queryset=ExternalStorageService.objects.all(),
        many=False,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    configured_storage_addons = HyperlinkedRelatedField(
        many=True,
        queryset=ConfiguredStorageAddon.objects.active(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
        required=False,
    )
    authorized_operations = DataclassRelatedLinkField(
        dataclass_model=AddonOperationModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    username = serializers.CharField(
        write_only=True
    )  # placeholder for ExternalCredentials integrity only not auth
    password = serializers.CharField(
        write_only=True
    )  # placeholder for ExternalCredentials integrity only not auth

    included_serializers = {
        "account_owner": "addon_service.serializers.UserReferenceSerializer",
        "external_storage_service": "addon_service.serializers.ExternalStorageServiceSerializer",
        "configured_storage_addons": "addon_service.serializers.ConfiguredStorageAddonSerializer",
        "authorized_operations": "addon_service.serializers.AddonOperationSerializer",
    }

    def create(self, validated_data):
        session_user_uri = self.context["request"].session.get("user_reference_uri")
        authorized_capabilities = validated_data["authorized_capabilities"]
        account_owner, _ = UserReference.objects.get_or_create(
            user_uri=session_user_uri
        )
        external_storage_service = validated_data["external_storage_service"]
        # TODO(ENG-5189): Update this once credentials format is finalized
        credentials, _ = ExternalCredentials.objects.get_or_create(
            oauth_key=validated_data["username"],
            oauth_secret=validated_data["password"],
        )

        # Set state token on related ExternalCredential model
        credentials.state_token = token_urlsafe(16)
        credentials.save()

        external_account, _ = ExternalAccount.objects.get_or_create(
            owner=account_owner,
            credentials=credentials,
            credentials_issuer=external_storage_service.credentials_issuer,
        )
        return AuthorizedStorageAccount.objects.create(
            external_storage_service=external_storage_service,
            external_account=external_account,
            authorized_capabilities=authorized_capabilities,
        )

    class Meta:
        model = AuthorizedStorageAccount
        fields = [
            "url",
            "account_owner",
            "configured_storage_addons",
            "default_root_folder",
            "external_storage_service",
            "username",
            "password",
            "authorized_capabilities",
            "authorized_operations",
            "authorized_operation_names",
            "auth_url",
        ]
