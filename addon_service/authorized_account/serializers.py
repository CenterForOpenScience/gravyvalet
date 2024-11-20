from __future__ import annotations

from typing import TYPE_CHECKING

from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError as ModelValidationError
from rest_framework_json_api import serializers

from addon_service.common.credentials_formats import CredentialsFormats
from addon_service.external_service.models import ExternalService
from addon_service.osf_models.fields import encrypt_string
from addon_service.serializer_fields import (
    CredentialsField,
    EnumNameMultipleChoiceField,
)
from addon_service.user_reference.models import UserReference
from addon_toolkit import AddonCapabilities


if TYPE_CHECKING:
    from addon_service.authorized_account.models import AuthorizedAccount

REQUIRED_FIELDS = frozenset(["url", "account_owner", "authorized_operations"])


class AuthorizedAccountSerializer(serializers.HyperlinkedModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Check whether subclasses declare all of required fields
        if not REQUIRED_FIELDS.issubset(set(self.fields.keys())):
            raise Exception(
                f"{self.__class__.__name__} requires {self.REQUIRED_FIELDS} to be instantiated"
            )

        # Check if it's a POST request and remove the field as it's not in our FE spec
        if "context" in kwargs and kwargs["context"]["request"].method == "POST":
            self.fields.pop("configured_storage_addons", None)

    display_name = serializers.CharField(
        allow_blank=True, allow_null=True, required=False, max_length=256
    )
    authorized_capabilities = EnumNameMultipleChoiceField(enum_cls=AddonCapabilities)
    authorized_operation_names = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    auth_url = serializers.CharField(read_only=True)
    api_base_url = serializers.URLField(
        allow_blank=True, required=False, allow_null=True
    )

    credentials = CredentialsField(write_only=True, required=False)
    initiate_oauth = serializers.BooleanField(write_only=True, required=False)

    included_serializers = {
        "account_owner": "addon_service.serializers.UserReferenceSerializer",
        "external_storage_service": "addon_service.serializers.ExternalStorageServiceSerializer",
        "configured_storage_addons": "addon_service.serializers.ConfiguredStorageAddonSerializer",
        "authorized_operations": "addon_service.serializers.AddonOperationSerializer",
    }

    def create_authorized_account(
        self,
        external_service: ExternalService,
        authorized_capabilities: AddonCapabilities,
        display_name: str = "",
        api_base_url: str = "",
        **kwargs,
    ) -> AuthorizedAccount:
        session_user_uri = self.context["request"].session.get("user_reference_uri")
        account_owner, _ = UserReference.objects.get_or_create(
            user_uri=session_user_uri
        )
        try:
            return self.Meta.model.objects.create(
                _display_name=display_name,
                external_service=external_service,
                account_owner=account_owner,
                authorized_capabilities=authorized_capabilities,
                api_base_url=api_base_url,
            )
        except ModelValidationError as e:
            raise serializers.ValidationError(e)

    def create(self, validated_data: dict) -> AuthorizedAccount:
        validated_data = self.fix_dotted_external_service(validated_data)
        authorized_account = self.create_authorized_account(**validated_data)
        return self.process_and_set_auth(authorized_account, validated_data)

    @staticmethod
    def fix_dotted_external_service(validated_data):
        if base_account_dict := validated_data.get("external_service"):
            validated_data["external_service"] = list(base_account_dict.values())[0]
        return validated_data

    def process_and_set_auth(
        self,
        authorized_account: AuthorizedAccount,
        validated_data: dict,
    ) -> AuthorizedAccount:
        if validated_data.get("initiate_oauth", False):
            if authorized_account.credentials_format is CredentialsFormats.OAUTH2:
                authorized_account.initiate_oauth2_flow(
                    validated_data.get("authorized_scopes")
                )
            elif authorized_account.credentials_format is CredentialsFormats.OAUTH1A:
                authorized_account.initiate_oauth1_flow()
                self.context["request"].session["oauth1a_account_id"] = encrypt_string(
                    f"{authorized_account.__class__.__name__}/{authorized_account.pk}"
                )
            else:
                raise serializers.ValidationError(
                    {
                        "initiate_oauth": "this external service is not configured for oauth"
                    }
                )
        elif validated_data.get("credentials"):
            authorized_account.credentials = validated_data["credentials"]
            authorized_account.imp_cls.confirm_credentials(
                authorized_account.credentials
            )

        try:
            authorized_account.save()
        except ModelValidationError as e:
            raise serializers.ValidationError(e)

        if authorized_account.credentials_format.is_direct_from_user:
            async_to_sync(authorized_account.execute_post_auth_hook)()

        return authorized_account

    def update(self, instance, validated_data):
        validated_data = self.fix_dotted_base_account(validated_data)
        # only these fields may be PATCHed:
        if "display_name" in validated_data:
            instance.display_name = validated_data["display_name"]
        if "authorized_capabilities" in validated_data:
            instance.authorized_capabilities = validated_data["authorized_capabilities"]
        if "api_base_url" in validated_data:
            instance.api_base_url = validated_data["api_base_url"]
        if "default_root_folder" in validated_data:
            instance.default_root_folder = validated_data["default_root_folder"]
        if validated_data.get("credentials"):
            instance.credentials = validated_data["credentials"]
        instance.save()  # may raise ValidationError
        if (
            validated_data.get("initiate_oauth", False)
            and instance.credentials_format is CredentialsFormats.OAUTH2
        ):
            instance.initiate_oauth2_flow(validated_data.get("authorized_scopes"))
        return instance

    class Meta:
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
            "credentials",
            "initiate_oauth",
            "credentials_available",
        ]
