from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError,
)
from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.utils import get_resource_type_from_model

from addon_service.common import (
    osf,
    view_names,
)
from addon_service.common.enum_serializers import EnumNameChoiceField
from addon_service.common.invocation_status import InvocationStatus
from addon_service.common.serializer_fields import DataclassRelatedDataField
from addon_service.models import (
    AddonOperationInvocation,
    AddonOperationModel,
    AuthorizedStorageAccount,
    ConfiguredStorageAddon,
    UserReference,
)
from addon_toolkit import (
    AddonOperationDeclaration,
    AddonOperationType,
)

from .perform import perform_invocation__blocking


RESOURCE_TYPE = get_resource_type_from_model(AddonOperationInvocation)


class AddonOperationInvocationSerializer(serializers.HyperlinkedModelSerializer):
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

    thru_account = ResourceRelatedField(
        many=False,
        required=False,
        queryset=AuthorizedStorageAccount.objects.active(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
    )
    thru_addon = ResourceRelatedField(
        many=False,
        required=False,
        queryset=ConfiguredStorageAddon.objects.active(),
        related_link_view_name=view_names.related_view(RESOURCE_TYPE),
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
        "thru_account": "addon_service.serializers.AuthorizedStorageAccountSerializer",
        "thru_addon": "addon_service.serializers.ConfiguredStorageAddonSerializer",
        "operation": "addon_service.serializers.AddonOperationSerializer",
        "by_user": "addon_service.serializers.UserReferenceSerializer",
    }

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
        _user_uri = _request.session.get("user_reference_uri")
        if not self._has_create_permission(
            _request, _user_uri, _operation, _thru_account, _thru_addon
        ):
            raise PermissionDenied
        ###
        # ok now do the creation
        _user, _ = UserReference.objects.get_or_create(user_uri=_user_uri)
        _invocation = AddonOperationInvocation.objects.create(
            operation=AddonOperationModel(_imp_cls, _operation),
            operation_kwargs=validated_data["operation_kwargs"],
            thru_addon=_thru_addon,
            thru_account=_thru_account,
            by_user=_user,
        )
        match _operation.operation_type:
            case AddonOperationType.REDIRECT | AddonOperationType.IMMEDIATE:
                perform_invocation__blocking(_invocation)
            case AddonOperationType.EVENTUAL:
                raise NotImplementedError("TODO: enqueue task")
            case _:
                raise ValueError(f"unknown operation type: {_operation.operation_type}")
        return _invocation

    def _has_create_permission(
        self,
        request,
        user_uri: str,
        operation: AddonOperationDeclaration,
        thru_account: AuthorizedStorageAccount,
        thru_addon: ConfiguredStorageAddon | None,
    ) -> bool:
        if thru_addon is None:
            # when invoking thru account, must be the owner
            return user_uri == thru_account.owner_uri
        # when invoking thru addon, may be either...
        return bool(
            # the addon owner:
            (user_uri == thru_addon.owner_uri)
            # or a user with "read" access on the connected osf project:
            or osf.has_osf_permission_on_resource(
                request,
                thru_addon.authorized_resource.resource_uri,
                osf.OSFPermission.for_capabilities(operation.capability),
            )
        )
