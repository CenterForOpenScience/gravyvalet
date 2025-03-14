from rest_framework.exceptions import ValidationError
from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.authorized_account.models import AuthorizedAccount
from addon_service.authorized_account.polymorphic_serializers import (
    AuthorizedAccountPolymorphicSerializer,
)
from addon_service.common import view_names
from addon_service.common.enum_serializers import EnumNameChoiceField
from addon_service.common.invocation_status import InvocationStatus
from addon_service.common.serializer_fields import (
    CustomPolymorphicResourceRelatedField,
    DataclassRelatedDataField,
)
from addon_service.configured_addon.models import ConfiguredAddon
from addon_service.configured_addon.polymorphic_serializers import (
    ConfiguredAddonPolymorphicSerializer,
)
from addon_service.models import (
    AddonOperationInvocation,
    AddonOperationModel,
    UserReference,
)
from app import settings


RESOURCE_TYPE = get_resource_type_from_model(AddonOperationInvocation)


class AddonOperationInvocationSerializer(serializers.HyperlinkedModelSerializer):
    """api serializer for the `AddonOperationInvocation` model"""

    class Meta:
        model = AddonOperationInvocation
        fields = [
            "id",
            "url",
            "invocation_status",
            "operation_kwargs",
            "operation_result",
            "operation",
            "by_user",
            "thru_account",
            "thru_addon",
            "created",
            "modified",
            "operation_name",
        ]

    url = serializers.HyperlinkedIdentityField(
        view_name=view_names.detail_view(RESOURCE_TYPE)
    )
    invocation_status = EnumNameChoiceField(enum_cls=InvocationStatus, read_only=True)
    operation_kwargs = serializers.JSONField()
    operation_result = serializers.JSONField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)
    operation_name = serializers.CharField(required=True)

    thru_account = CustomPolymorphicResourceRelatedField(
        many=False,
        required=False,
        queryset=AuthorizedAccount.objects.active(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
        polymorphic_serializer=AuthorizedAccountPolymorphicSerializer,
    )
    thru_addon = CustomPolymorphicResourceRelatedField(
        many=False,
        required=False,
        queryset=ConfiguredAddon.objects.active().select_related(
            "base_account__external_service",
            "base_account__authorizedstorageaccount",
            "base_account__authorizedcitationaccount",
            "base_account__account_owner",
        ),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
        polymorphic_serializer=ConfiguredAddonPolymorphicSerializer,
    )

    by_user = ResourceRelatedField(
        many=False,
        read_only=True,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )

    operation = DataclassRelatedDataField(
        dataclass_model=AddonOperationModel,
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
        read_only=True,
    )

    included_serializers = {
        "thru_account": "addon_service.serializers.AuthorizedAccountPolymorphicSerializer",
        "thru_addon": "addon_service.serializers.ConfiguredAddonPolymorphicSerializer",
        "operation": "addon_service.serializers.AddonOperationSerializer",
        "by_user": "addon_service.serializers.UserReferenceSerializer",
    }

    def to_internal_value(self, data):
        validated_data = super().to_internal_value(data)
        return validated_data

    def create(self, validated_data):
        _thru_addon = validated_data.get("thru_addon")
        _thru_account = validated_data.get("thru_account")
        if _thru_addon is None and _thru_account is None:
            raise ValidationError("must include either 'thru_addon' or 'thru_account'")
        if _thru_account is None:
            _thru_account = _thru_addon.base_account
        _operation_name: str = validated_data["operation_name"]
        _imp_cls = _thru_account.imp_cls
        _operation = _imp_cls.get_operation_declaration(_operation_name)
        _request = self.context["request"]
        _user_uri = (
            _request.session.get("user_reference_uri")
            or f"{settings.OSF_BASE_URL}/anonymous"
        )
        _user, _ = UserReference.objects.get_or_create(user_uri=_user_uri)
        return AddonOperationInvocation(
            operation=AddonOperationModel(_imp_cls.ADDON_INTERFACE, _operation),
            operation_kwargs=validated_data["operation_kwargs"],
            thru_addon=_thru_addon,
            thru_account=_thru_account,
            by_user=_user,
        )
